import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import google.generativeai as genai
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 2. 한글 폰트 설정 (이 부분이 추가되었습니다!)
font_path = 'NanumGothic.ttf' # 같은 폴더에 있는 폰트 파일 지정

if os.path.exists(font_path):
    # 폰트 파일이 있으면 로드해서 기본 폰트로 설정
    font_prop = fm.FontProperties(fname=font_path)
    font_name = font_prop.get_name()
    plt.rc('font', family=font_name)
    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False
else:
    # 폰트 파일이 없으면 경고 메시지 (하지만 프로그램은 돌아가게 함)
    st.warning("⚠️ 'NanumGothic.ttf' 파일을 찾을 수 없습니다. 한글이 깨질 수 있습니다.")

# 3. 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("세 권의 책을 입력하면, 취향을 분석하여 새로운 책들을 연결해 드립니다.")

# 4. API 키 설정 (Streamlit Secrets 사용)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception:
    st.error("API 키가 설정되지 않았습니다. Streamlit 설정을 확인해주세요.")

# 5. 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 6. 그래프 생성 로직
def create_graph(books):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
        text = response.text.replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        st.error(f"데이터 생성 중 오류가 발생했습니다: {e}")
        return None

# 7. 메인 실행 및 시각화
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 책들의 관계를 분석하고 있습니다..."):
        data = create_graph([book1, book2, book3])
        
        if data:
            G = nx.Graph()
            
            for node in data['nodes']:
                G.add_node(node['id'], group=node.get('group', 1))
            
            for edge in data['edges']:
                G.add_edge(edge['source'], edge['target'], label=edge.get('label', ''))

            plt.figure(figsize=(12, 8))
            
            # 레이아웃 설정
            pos = nx.spring_layout(G, k=0.8) # k값을 키우면 노드 간격이 더 벌어집니다
            
            # 노드 그리기
            nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', alpha=0.9)
            
            # 라벨(텍스트) 그리기 - 여기서 위에서 설정한 폰트가 적용됩니다
            nx.draw_networkx_labels(G, pos, font_family=plt.rcParams['font.family'], font_size=10)
            
            # 엣지 그리기
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, edge_color='gray')
            
            st.pyplot(plt)
            st.success("네트워크 생성이 완료되었습니다!")
            
            with st.expander("추천 상세 이유 보기"):
                for edge in data['edges']:
                    st.write(f"- **{edge['source']}** ➡️ **{edge['target']}**: {edge['label']}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
