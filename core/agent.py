import time
import platform

import psutil
import requests

from core.vlm_handler import VLMHandler
from core.rag_pipeline import RAGPipeline
from core.reward_system import MultiArmedBandit
from core.providers import ProviderManager
from core.session import StepEvent
from core.config import OLLAMA_BASE_URL
from core.hf_models import get_hf
from core.guardrails import InputGuardrails, OutputGuardrails
from core.database import feedback_log_add
from core.agent_base import AgentInput
from core.agent_orchestrator import AgentOrchestrator
from models.schemas import AgentState


class DebugAgent:
    def __init__(self, providers: ProviderManager | None = None):
        self.providers = providers or ProviderManager.load()
        self.vlm = VLMHandler(providers=self.providers)
        self.rag = RAGPipeline(providers=self.providers)
        self.bandit = MultiArmedBandit(n_arms=3)
        self._hf = get_hf()
        self._current_session_id = ""
        self._start_time = 0.0
        self._total_tokens_sent = 0
        self._total_tokens_received = 0
        self._last_speed = 0.0
        self._os_info = f"{platform.system()}{platform.machine().replace('AMD64', '64').replace('x86_64', '64')} · Python {platform.python_version()}"
        self._orchestrator = AgentOrchestrator(providers=self.providers)
        self._current_arm_cfg = {}

    def extract_error(self, image_path: str) -> str:
        from PIL import Image
        image = Image.open(image_path)
        return self.vlm.extract_text(image)

    def _classify_and_enrich(self, error_text: str) -> dict:
        enrichment = {}
        if self._hf.available:
            enrichment["error_type"] = self._hf.classify_error_type(error_text)
            enrichment["language"] = self._hf.classify_language(error_text)
        else:
            enrichment["error_type"] = "unknown"
            enrichment["language"] = "unknown"
        return enrichment

    def solve(self, error_text: str, stream: bool = False, history: list | None = None, context: dict | None = None):
        self._start_time = time.time()
        state = AgentState(error_text=error_text, guardrails_passed=True)
        state.arm_selected = self.bandit.select_arm()
        arm_cfg = self.bandit.get_arm_config(state.arm_selected)
        state.arm_config = arm_cfg
        self._current_arm_cfg = arm_cfg
        enrichment = self._classify_and_enrich(error_text)

        guardrail_msgs = []
        input_check = InputGuardrails.check_length(error_text)
        if not input_check.passed:
            state.guardrails_passed = False
            guardrail_msgs.append(input_check.message)
        sensitive_check = InputGuardrails.check_sensitive_data(error_text)
        clean_text = sensitive_check.sanitized or error_text
        if sensitive_check.message:
            guardrail_msgs.append(sensitive_check.message)
        dangerous_check = InputGuardrails.check_dangerous_code(clean_text)
        if not dangerous_check.passed:
            state.guardrails_passed = False
            guardrail_msgs.append(dangerous_check.message)
        state.guardrail_message = "; ".join(guardrail_msgs)

        events_collected = []

        def event_handler(event: StepEvent):
            events_collected.append(event)

        self._orchestrator.on_event(event_handler)

        arm_label = arm_cfg.get("label", "Balanced")
        num_docs = arm_cfg.get("num_docs", 5)

        def event_stream():
            yield StepEvent(type="think", content=f"Arm: {arm_label} ({arm_cfg.get('prompt_style', 'balanced')})")

            if not state.guardrails_passed:
                yield StepEvent(type="error", content=f"Guardrail blocked: {state.guardrail_message}")
                return
            if state.guardrail_message:
                yield StepEvent(type="think", content=f"Guardrail: {state.guardrail_message}")
            if enrichment.get("language", "unknown") != "unknown":
                yield StepEvent(type="think", content=f"Detected language: {enrichment['language']}")
            if enrichment.get("error_type", "unknown") != "unknown":
                yield StepEvent(type="think", content=f"Error type: {enrichment['error_type']}")

            ctx = context or {}
            inp = AgentInput(
                query=clean_text,
                context=clean_text,
                images=ctx.get("images", []),
                files=ctx.get("files", []),
                history=history or [],
                metadata={
                    "arm": state.arm_selected,
                    "arm_config": arm_cfg,
                    "enrichment": enrichment,
                    "num_docs": num_docs,
                    "vlm_text": ctx.get("vlm_text", ""),
                    "file_contents": ctx.get("file_contents", {}),
                    "language": enrichment.get("language", "unknown"),
                    "error_type": enrichment.get("error_type", "unknown"),
                    "style_instruction": arm_cfg.get("prompt_style", "balanced"),
                },
            )

            output = self._orchestrator.run(inp)

            for ev in events_collected:
                if ev.type in ("think", "retrieve", "tool"):
                    yield ev
                elif ev.type == "error":
                    yield ev

            if not output.success:
                state.error = output.error
                yield StepEvent(type="error", content=output.error)
                return

            final_solution = output.content
            output_check = OutputGuardrails.check_dangerous_code(final_solution)
            if not output_check.passed:
                yield StepEvent(type="error", content=output_check.message)
                return
            out_sensitive = OutputGuardrails.check_sensitive_data(final_solution)
            final_solution = out_sensitive.sanitized

            state.solution = final_solution
            agent_results = output.data.get("agent_results", {})
            state.agent_results = agent_results
            if "knowledge" in agent_results:
                state.retrieved_docs = agent_results["knowledge"]["output"].data.get("docs", [])
            if "research" in agent_results:
                state.web_results = agent_results["research"]["output"].data.get("results", [])

            if stream:
                yield StepEvent(type="generate", content=final_solution, metadata={"partial": False})
            else:
                yield StepEvent(type="generate", content=final_solution, metadata={"partial": False})

        if stream:
            return event_stream(), state
        return state

    def handle_feedback(self, arm: int, rating: int, query: str = "", solution: str = ""):
        self.bandit.update(arm, reward=float(rating))
        latency = (time.time() - self._start_time) * 1000 if self._start_time else 0
        try:
            feedback_log_add(
                session_id=self._current_session_id,
                arm=arm,
                rating=rating,
                error_text=query,
                model="",
                latency_ms=latency,
            )
        except Exception:
            pass
        if rating == 1 and query and solution:
            try:
                from core.kb_manager import KbManager
                mgr = KbManager(providers=self.providers)
                mgr.learn_from_feedback(query, solution)
                mgr.close()
            except Exception as exc:
                logger.debug("Auto-learn from feedback skipped: %s", exc)

    def bandit_stats(self) -> dict:
        return self.bandit.stats()

    def cleanup(self):
        import gc
        if hasattr(self, 'rag') and self.rag:
            self.rag.close()
        if hasattr(self, '_orchestrator') and self._orchestrator:
            self._orchestrator.reset()
        try:
            from core.hf_models import reset_hf
            reset_hf()
        except Exception:
            pass
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def reload_providers(self):
        self.cleanup()
        self.providers = ProviderManager.load()
        self.vlm = VLMHandler(providers=self.providers)
        self.rag = RAGPipeline(providers=self.providers)
        self._orchestrator = AgentOrchestrator(providers=self.providers)

    def ping_ollama(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def get_token_stats(self) -> dict:
        return {
            "sent": self._total_tokens_sent,
            "received": self._total_tokens_received,
            "speed": self._last_speed,
        }

    def get_memory_usage(self) -> int:
        try:
            return int(psutil.Process().memory_info().rss / (1024 * 1024))
        except (psutil.Error, AttributeError):
            return 0

    def get_active_model_names(self) -> dict:
        llm = self.providers.get_active_model(self.providers.llm, "qwen3-coder:30b")
        vlm = self.providers.get_active_model(self.providers.vlm, "llava:7b")
        embed = self.providers.get_active_model(self.providers.embedding, "mxbai-embed-large")
        return {"llm": llm, "vlm": vlm, "embedding": embed}

    def get_provider_info(self) -> dict:
        cfg = self.providers.llm
        return {
            "type": cfg.provider_type,
            "endpoint": cfg.base_url or OLLAMA_BASE_URL,
        }

    def get_os_info(self) -> str:
        return self._os_info

    def get_orchestrator(self) -> AgentOrchestrator:
        return self._orchestrator

    def set_workflow_mode(self, mode: str):
        self._orchestrator.set_workflow_mode(mode)

    def list_agents(self) -> list[dict]:
        return self._orchestrator.list_agents()
