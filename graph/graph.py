from langgraph.graph import END, START, StateGraph
from database.sqlite import SQLiteRepository
from graph.nodes import analysis_node, analytics_node, extract_node, history_node, response_node, risks_node
from graph.state import FitnessState


def build_graph(repository: SQLiteRepository):
    workflow = StateGraph(FitnessState)
    workflow.add_node("extract", extract_node)
    workflow.add_node("history", history_node(repository))
    workflow.add_node("analytics", analytics_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("risks", risks_node)
    workflow.add_node("response", response_node)
    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "history")
    workflow.add_edge("history", "analytics")
    workflow.add_edge("analytics", "analysis")
    workflow.add_edge("analytics", "risks")
    # The response runs only when both parallel branches have completed.
    workflow.add_edge(["analysis", "risks"], "response")
    workflow.add_edge("response", END)
    return workflow.compile()
