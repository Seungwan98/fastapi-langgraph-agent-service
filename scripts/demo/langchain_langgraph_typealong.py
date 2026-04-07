from __future__ import annotations

import argparse
from typing import TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ChainGraphState(TypedDict):
    topic: str
    answer: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")


def build_langchain_model() -> ChatOpenAI:
    settings = Settings()
    api_key = SecretStr(settings.openai_api_key) if settings.openai_api_key else None
    return ChatOpenAI(model=settings.openai_model, api_key=api_key)

def build_langchain_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", "초보자에게 처음으로 알려주는 도우미"),
        ("human", "사용자 고민: {topic}\n불안 정도: {level}")
    ])

def build_langchain_chain():
    prompt = build_langchain_prompt()
    model = build_langchain_model()
    parser = StrOutputParser()
    return prompt | model | parser

def run_langchain_demo():
    chain = build_langchain_chain()
    topic = "안녕!! 나 처음이라 어색해!"
    level = "7/10"
    
    answer = chain.invoke({"topic": topic, "level": level})
    
    print("answer :::")
    print(answer)

def run_langchain_deep_demo():
    variables = {
        "topic": "안녕!! 나 처음이라 어색해!",
        "level": "7/10",
    }

    prompt = build_langchain_prompt()
    prompt_value = prompt.invoke(variables)
    print("=== 1. prompt 결과 ===")
    print(prompt_value)
    print()

    messages = prompt_value.to_messages()
    print("=== 2. prompt를 message list로 바꾼 결과 ===")
    print(messages)
    print()

    model = build_langchain_model()
    raw_response = model.invoke(messages)
    print("=== 3. model raw output ===")
    print(type(raw_response))
    print(raw_response)
    print()

    parser = StrOutputParser()
    parsed_text = parser.invoke(raw_response)
    print("=== 4. parser 적용 후 ===")
    print(parsed_text)
    print()

    chain = build_langchain_chain()
    final_answer = chain.invoke(variables)
    print("=== 5. chain 전체 실행 결과 ===")
    print(final_answer)

def main() -> int:
    parser = argparse.ArgumentParser(description="LangChain learning demo")
    parser.add_argument("--mode", choices=["simple", "deep"], default="simple")
    args = parser.parse_args()

    if args.mode == "deep":
        run_langchain_deep_demo()
    else:
        run_langchain_demo()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())



# def build_langgraph_from_chain():
#     chain = build_langchain_chain()

#     def ask_chain(state: ChainGraphState) -> ChainGraphState:
#         # LangGraph 노드는 state를 입력으로 받아, 바뀐 state를 다시 반환한다.
#         answer = chain.invoke({"topic": state["topic"]})
#         return {"topic": state["topic"], "answer": answer}

#     # StateGraph(...)는 state를 흘려 보내는 워크플로 틀이다.
#     workflow = StateGraph(ChainGraphState)
#     workflow.add_node("ask_chain", ask_chain)
#     workflow.add_edge("ask_chain", END)
#     workflow.set_entry_point("ask_chain")

#     # compile()하면 정의만 있던 그래프가 실제 실행 가능한 객체가 된다.
#     return workflow.compile()


# def run_langgraph_demo() -> None:
#     graph = build_langgraph_from_chain()

#     # graph.invoke(...)는 초기 state를 넣고 노드 흐름을 한 번 실행한다.
#     state = graph.invoke({"topic": "두통이 있는데 너무 큰 병일까 불안해", "answer": ""})

#     print("\n[STEP 2] LangGraph wraps the LangChain chain")
#     print("- 최종 state:", state)
#     print("- 핵심: LangGraph는 state를 흘려 보내고, 노드가 그 state를 바꾼다.")


# def build_checkpoint_demo_graph():
#     # 응답을 여러 개 준비해 두면 같은 thread_id 호출이 이어지는 모습을 쉽게 볼 수 있다.
#     model = FakeListChatModel(
#         responses=[
#             "첫 번째 답변이에요. 같은 thread_id면 이 대화가 이어집니다.",
#             "두 번째 답변이에요. 이번에는 이전 메시지가 이미 state 안에 들어 있어요.",
#             "새 thread_id라서 완전히 새 대화처럼 시작합니다.",
#         ]
#     )

#     def chatbot(state: MessagesState) -> MessagesState:
#         # MessagesState는 {"messages": [...]} 형태의 대화 상태라고 생각하면 된다.
#         response = model.invoke(state["messages"])
#         return {"messages": [response]}

#     # 이번 단계는 일반 dict 대신 MessagesState를 그대로 써서 대화형 state를 보여 준다.
#     workflow = StateGraph(MessagesState)
#     workflow.add_node("chatbot", chatbot)
#     workflow.add_edge("chatbot", END)
#     workflow.set_entry_point("chatbot")

#     # checkpointer를 붙이면 thread_id 기준으로 state를 이어서 저장할 수 있다.
#     return workflow.compile(checkpointer=InMemorySaver())


# def run_checkpoint_demo() -> None:
#     graph = build_checkpoint_demo_graph()

#     # 같은 thread_id면 같은 대화 상태를 이어쓴다.
#     first = graph.invoke(
#         {"messages": [HumanMessage(content="안녕, 나 너무 불안해")]},
#         config={"configurable": {"thread_id": "demo-thread"}},
#     )

#     second = graph.invoke(
#         {"messages": [HumanMessage(content="조금 더 설명해 줘")]},
#         config={"configurable": {"thread_id": "demo-thread"}},
#     )

#     # 다른 thread_id를 쓰면 완전히 새 대화 state가 시작된다.
#     new_thread = graph.invoke(
#         {"messages": [HumanMessage(content="새로운 대화 시작") ]},
#         config={"configurable": {"thread_id": "fresh-thread"}},
#     )

#     print("\n[STEP 3] LangGraph checkpoint + thread_id")
#     print("- 같은 thread 첫 호출 message 개수:", len(first["messages"]))
#     print("- 같은 thread 두 번째 호출 message 개수:", len(second["messages"]))
#     print("- 다른 thread 호출 message 개수:", len(new_thread["messages"]))
#     print("- 핵심: 같은 thread_id면 이전 messages가 이어지고, 다른 thread_id면 새 state가 시작된다.")


# def main() -> int:
#     parser = argparse.ArgumentParser(description="Tiny LangChain + LangGraph type-along demo.")
#     parser.add_argument(
#         "--step",
#         choices=["1", "2", "3", "all"],
#         default="all",
#         help="1=LangChain, 2=LangGraph, 3=Checkpoint, all=run everything",
#     )
#     args = parser.parse_args()

#     if args.step in {"1", "all"}:
#         run_langchain_demo()
#     if args.step in {"2", "all"}:
#         run_langgraph_demo()
#     if args.step in {"3", "all"}:
#         run_checkpoint_demo()

#     return 0
