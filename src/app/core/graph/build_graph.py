from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.core.graph.state import GraphState


def build_graph(model_turn_node, execute_command_node):
    graph = StateGraph(GraphState)
    graph.add_node("model_turn", model_turn_node)
    graph.add_node("execute_command", execute_command_node)

    def route_after_model(state: GraphState):
        if state.get("status") == "waiting_approval":
            return END
        if state.get("pending_approval"):
            return "execute_command"
        if state.get("status") in {"completed", "failed"}:
            return END
        return "model_turn"

    def route_after_execute(state: GraphState):
        if state.get("status") in {"failed", "completed"}:
            return END
        return "model_turn"

    graph.add_edge(START, "model_turn")
    graph.add_conditional_edges("model_turn", route_after_model, ["execute_command", "model_turn", END])
    graph.add_conditional_edges("execute_command", route_after_execute, ["model_turn", END])
    return graph
