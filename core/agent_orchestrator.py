import time
from typing import Optional

from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.agents import create_agent
from core.config import AGENT_CONFIGS, DEFAULT_WORKFLOW_MODE
from core.message_bus import MessageBus
from core.session import StepEvent


class AgentOrchestrator:
    def __init__(self, providers=None):
        self.providers = providers
        self.bus = MessageBus()
        self._agents: dict[str, BaseAgent] = {}
        self._event_handlers: list[callable] = []
        self._workflow_mode = DEFAULT_WORKFLOW_MODE
        self._init_default_agents()

    def _init_default_agents(self):
        for agent_name in AGENT_CONFIGS:
            cfg = AGENT_CONFIGS[agent_name]
            if not cfg.get("enabled", True):
                continue
            agent = create_agent(agent_name, providers=self.providers)
            self.register_agent(agent)

    def register_agent(self, agent: BaseAgent):
        self._agents[agent.config.name] = agent
        agent.on_event(lambda e: self._forward_event(e))
        self.bus.subscribe(agent.config.name, lambda msg: None)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def list_agents(self, enabled_only: bool = True) -> list[dict]:
        result = []
        for name, agent in self._agents.items():
            if enabled_only and not agent.config.enabled:
                continue
            result.append({
                "name": name,
                "enabled": agent.config.enabled,
                "tools": agent.list_tools(),
            })
        return result

    def on_event(self, handler: callable):
        self._event_handlers.append(handler)

    def _forward_event(self, event: StepEvent):
        for handler in self._event_handlers:
            handler(event)

    def run(self, inp: AgentInput) -> AgentOutput:
        self._forward_event(StepEvent(type="think", content="Orchestrator: starting multi-agent pipeline..."))
        plan = self._build_plan(inp)
        mode = plan.get("workflow_mode", self._workflow_mode)
        self._forward_event(StepEvent(type="think", content=f"Orchestrator: mode={mode}, {len(plan['agents'])} agents"))
        results = {}
        if mode == "sequential":
            results = self._run_sequential(plan, inp)
        elif mode == "parallel":
            results = self._run_parallel(plan, inp)
        else:
            results = self._run_dynamic(plan, inp)
        final = self._combine_results(results, inp)
        return final

    def _build_plan(self, inp: AgentInput) -> dict:
        agents = []
        has_image = bool(inp.images)
        has_files = bool(inp.files)
        if has_image and "vision" in self._agents and self._agents["vision"].config.enabled:
            agents.append("vision")
        if "guardian" in self._agents and self._agents["guardian"].config.enabled:
            agents.append("guardian")
        if "classifier" in self._agents and self._agents["classifier"].config.enabled:
            agents.append("classifier")
        if "knowledge" in self._agents and self._agents["knowledge"].config.enabled:
            agents.append("knowledge")
        if "research" in self._agents and self._agents["research"].config.enabled:
            agents.append("research")
        if has_files and "code_agent" in self._agents and self._agents["code_agent"].config.enabled:
            agents.append("code_agent")
        if "solver" in self._agents and self._agents["solver"].config.enabled:
            agents.append("solver")
        if "validator" in self._agents and self._agents["validator"].config.enabled:
            agents.append("validator")
        return {"workflow_mode": self._workflow_mode, "agents": agents, "total": len(agents)}

    def _run_sequential(self, plan: dict, inp: AgentInput) -> dict:
        results = {}
        for agent_name in plan.get("agents", []):
            agent = self._agents.get(agent_name)
            if not agent or not agent.config.enabled:
                continue
            agent_inp = self._build_agent_input(agent_name, inp, results)
            t0 = time.time()
            self._forward_event(StepEvent(type="think", content=f"Routing to {agent_name}..."))
            output = agent.run(agent_inp)
            dt = (time.time() - t0) * 1000
            results[agent_name] = {"output": output, "duration_ms": dt}
            status = "done" if output.success else "failed"
            self._forward_event(StepEvent(type="generate", content=f"{agent_name}: {status} ({dt:.0f}ms)"))
        return results

    def _run_parallel(self, plan: dict, inp: AgentInput) -> dict:
        import concurrent.futures
        results = {}
        agent_names = plan.get("agents", [])
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {}
            for agent_name in agent_names:
                agent = self._agents.get(agent_name)
                if not agent or not agent.config.enabled:
                    continue
                agent_inp = self._build_agent_input(agent_name, inp, results)
                future = executor.submit(agent.run, agent_inp)
                future_map[future] = agent_name
            for future in concurrent.futures.as_completed(future_map):
                name = future_map[future]
                t0 = time.time()
                try:
                    output = future.result()
                    dt = (time.time() - t0) * 1000
                    results[name] = {"output": output, "duration_ms": dt}
                    status = "done" if output.success else "failed"
                    self._forward_event(StepEvent(type="generate", content=f"{name}: {status} ({dt:.0f}ms)"))
                except Exception as e:
                    results[name] = {"output": AgentOutput(success=False, error=str(e)), "duration_ms": 0}
                    self._forward_event(StepEvent(type="error", content=f"{name}: {e}"))
        return results

    def _run_dynamic(self, plan: dict, inp: AgentInput) -> dict:
        return self._run_sequential(plan, inp)

    def _build_agent_input(self, agent_name: str, inp: AgentInput, previous_results: dict) -> AgentInput:
        metadata = dict(inp.metadata)
        for prev_name, prev_data in previous_results.items():
            metadata[prev_name] = prev_data.get("output", AgentOutput()).to_dict() if hasattr(prev_data.get("output"), "to_dict") else {}
        return AgentInput(
            query=inp.query,
            context=inp.context,
            images=inp.images if agent_name == "vision" else [],
            files=inp.files if agent_name == "code_agent" else [],
            history=inp.history,
            metadata=metadata,
        )

    def _combine_results(self, results: dict, inp: AgentInput) -> AgentOutput:
        if "validator" in results:
            v = results["validator"]["output"]
            if v.success and v.content:
                return AgentOutput(success=True, content=v.content, data={"agent_results": results})
        if "solver" in results:
            s = results["solver"]["output"]
            if s.success and s.content:
                return AgentOutput(success=True, content=s.content, data={"agent_results": results})
        for name, data in reversed(list(results.items())):
            output = data["output"]
            if output.success and output.content:
                return AgentOutput(success=True, content=output.content, data={"agent_results": results})
        for name, data in results.items():
            output = data["output"]
            if output.content:
                return AgentOutput(success=True, content=output.content, data={"agent_results": results})
        return AgentOutput(success=False, content="", error="No agent produced a result", data={"agent_results": results})

    def set_workflow_mode(self, mode: str):
        if mode in ("sequential", "parallel", "dynamic"):
            self._workflow_mode = mode

    def reset(self):
        for agent in self._agents.values():
            agent.reset()

    def __repr__(self) -> str:
        return f"<AgentOrchestrator agents={len(self._agents)} mode={self._workflow_mode}>"
