import time
from core.agent_base import BaseAgent, AgentConfig, AgentInput, AgentOutput
from core.config import AGENT_CONFIGS
from core.message_bus import MessageBus


class OrchestratorAgent(BaseAgent):
    def __init__(self, config: AgentConfig | None = None, providers=None):
        super().__init__(config or AgentConfig.from_dict(AGENT_CONFIGS["orchestrator"]), providers)
        self.bus = MessageBus()
        self._agent_instances: dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent):
        self._agent_instances[agent.config.name] = agent
        self.bus.subscribe(agent.config.name, lambda msg, a=agent: self._route_to_agent(a, msg))

    def _route_to_agent(self, agent: BaseAgent, msg):
        pass

    def run(self, inp: AgentInput) -> AgentOutput:
        self.emit_event("think", "Orchestrator: planning workflow...")
        plan = self._build_workflow(inp)
        self.emit_event("think", f"Orchestrator: workflow={plan.get('workflow_mode', 'sequential')}, steps={len(plan.get('steps', []))}")
        results = []
        for step in plan.get("steps", []):
            agent_name = step.get("agent", "")
            agent = self._agent_instances.get(agent_name)
            if not agent or not agent.config.enabled:
                continue
            self.emit_event("think", f"Routing to {agent_name}...")
            t0 = time.time()
            agent_inp = AgentInput(
                query=inp.query,
                context=step.get("context", inp.context),
                images=inp.images,
                files=inp.files,
                history=inp.history,
                metadata={**inp.metadata, "parent_plan": plan},
            )
            output = agent.run(agent_inp)
            dt = (time.time() - t0) * 1000
            results.append({"agent": agent_name, "output": output, "duration_ms": dt})
            inp.metadata[agent_name] = output.to_dict()
            self.emit_event("generate", f"{agent_name}: done ({dt:.0f}ms)")
        combined = self._combine_results(results)
        return AgentOutput(success=True, content=combined, data={"plan": plan, "steps": results})

    def _build_workflow(self, inp: AgentInput) -> dict:
        has_image = bool(inp.images)
        steps = []
        if has_image:
            steps.append({"agent": "vision", "context": ""})
        steps.append({"agent": "guardian", "context": ""})
        steps.append({"agent": "classifier", "context": ""})
        steps.append({"agent": "knowledge", "context": ""})
        steps.append({"agent": "research", "context": ""})
        steps.append({"agent": "code_agent", "context": ""})
        steps.append({"agent": "solver", "context": ""})
        steps.append({"agent": "validator", "context": ""})
        return {"workflow_mode": "sequential", "steps": steps, "total": len(steps)}

    def _combine_results(self, results: list[dict]) -> str:
        for r in reversed(results):
            if r["output"].success and r["output"].content:
                return r["output"].content
        return ""

    def get_agent(self, name: str) -> BaseAgent | None:
        return self._agent_instances.get(name)

    def list_agents(self) -> list[dict]:
        return [{"name": n, "enabled": a.config.enabled} for n, a in self._agent_instances.items()]
