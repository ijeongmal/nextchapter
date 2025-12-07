import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import google.generativeai as genai
import json

# 페이지 기본 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("세 권의 책을 입력하면, 취향을 분석하여 새로운 책들을 연결해 드립니다.")

# API 키 설정 (Streamlit Secrets에서 가져옴)
# 주의: 이 코드는 Streamlit Cloud에 배포 후 'Secrets'에 API 키를 등록해야 작동합니다.
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception:
    st.error("API 키가 설정되지 않았습니다. Streamlit 설정을 확인해주세요.")

# 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 그래프 생성 함수
def create_graph(books):
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    다음 3권의 책을 기반으로 도서 추천 네트워크를 만들어줘: {books}
    
    [조건]
    1. 입력된 3권의 책 각각에 대해, 문체/난이도/철학이 유사한 연관 도서를 2~3권씩 추천해줘.
    2. 추천된 책들끼리도 연관성이 있다면 연결해줘.
    3. 결과는 반드시 오직 JSON 형식으로만 출력해. 다른 말은 하지 마.
    
    [JSON 형식 예시]
    {{
        "nodes": [
            {{"id": "책제목1", "group": 1}},
            {{"id": "책제목2", "group": 2}}
        ],
        "edges": [
            {{"source": "책제목1", "target": "책제목2", "label": "유사한 허무주의"}}
        ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON 부분만 추출 (가끔 ```json ... ``` 으로 감싸져 나올 때를 대비)
        text = response.text.replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        st.error(f"데이터 생성 중 오류가 발생했습니다: {e}")
        return None

# 메인 화면 로직
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 책들의 관계를 분석하고 있습니다..."):
        data = create_graph([book1, book2, book3])
        
        if data:
            # 그래프 그리기
            G = nx.Graph()
            
            # 노드 추가
            for node in data['nodes']:
                G.add_node(node['id'], group=node.get('group', 1))
            
            # 엣지 추가
            for edge in data['edges']:
                G.add_edge(edge['source'], edge['target'], label=edge.get('label', ''))

            # 시각화 설정
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, k=0.5)  # k값으로 노드 간격 조절
            
            # 노드 그리기
            nx.draw_networkx_nodes(G, pos, node_size=2000, node_color='lightblue', alpha=0.9)
            nx.draw_networkx_labels(G, pos, font_family='Malgun Gothic', font_size=10) # 한글 폰트 설정 필요시 수정
            
            # 엣지 그리기
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, edge_color='gray')
            
            st.pyplot(plt)
            st.success("네트워크 생성이 완료되었습니다!")
            
            # 텍스트로 추천 이유 보기
            with st.expander("추천 상세 이유 보기"):
                for edge in data['edges']:
                    st.write(f"- **{edge['source']}** ➡️ **{edge['target']}**: {edge['label']}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
