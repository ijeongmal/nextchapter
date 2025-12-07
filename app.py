import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import requests  # 구글 서버와 직접 통신하는 도구
import json
import os

# 1. 페이지 기본 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 2. 한글 폰트 설정 (안전장치 포함)
font_path = 'NanumGothic.ttf'
font_name = 'sans-serif' # 기본값

try:
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        font_name = font_prop.get_name()
        plt.rc('font', family=font_name)
        plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass # 폰트 설정 실패 시 조용히 넘어감

# 3. 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("세 권의 책을 입력하면, 취향을 분석하여 새로운 책들을 연결해 드립니다.")

# 4. API 키 가져오기 (Streamlit Secrets에서)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ API 키 설정을 확인해주세요. (Manage app -> Secrets)")
    st.stop()

# 5. 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 6. 그래프 생성 로직 (Gemini 2.5 Flash 사용)
def create_graph(books):
    # 🌟 [수정됨] gemini-2.5-flash 모델 주소로 변경
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    다음 3권의 책을 기반으로 도서 추천 네트워크를 만들어줘: {books}
    
    [조건]
    1. 입력된 3권의 책 각각에 대해, 문체/난이도/철학이 유사한 연관 도서를 2~3권씩 추천해줘.
    2. 추천된 책들끼리도 연관성이 있다면 연결해줘.
    3. 결과는 반드시 오직 JSON 형식으로만 출력해. 마크다운(```json)이나 다른 말은 절대 하지 마.
    
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
    
    # 요청 데이터 구성
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        # 구글 서버에 직접 요청 전송
        response = requests.post(url, json=payload)
        response.raise_for_status() # 에러 체크
        
        # 응답 데이터 파싱
        result = response.json()
        
        # 안전하게 텍스트 추출
        if 'candidates' in result and result['candidates']:
            text = result['candidates'][0]['content']['parts'][0]['text']
            
            # JSON 포맷 정리
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        else:
            return None
            
    except Exception as e:
        st.error(f"데이터 생성 중 오류가 발생했습니다: {e}")
        return None

# 7. 메인 실행 및 시각화
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI(Gemini 2.5)가 책들의 관계를 분석하고 있습니다..."):
        data = create_graph([book1, book2, book3])
        
        if data:
            # 그래프 객체 생성
            G = nx.Graph()
            
            # 노드 추가
            for node in data.get('nodes', []):
                G.add_node(node['id'], group=node.get('group', 1))
            
            # 엣지 추가
            for edge in data.get('edges', []):
                G.add_edge(edge['source'], edge['target'], label=edge.get('label', ''))

            # 시각화 설정
            plt.figure(figsize=(12, 8))
            
            # 레이아웃 (노드 배치)
            pos = nx.spring_layout(G, k=0.8)
            
            # 그리기
            nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', alpha=0.9)
            nx.draw_networkx_labels(G, pos, font_family=font_name, font_size=10)
            nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, edge_color='gray')
            
            # 화면 출력
            st.pyplot(plt)
            st.success("네트워크 생성이 완료되었습니다!")
            
            # 상세 이유 출력
            with st.expander("추천 상세 이유 보기"):
                for edge in data.get('edges', []):
                    source = edge.get('source', '?')
                    target = edge.get('target', '?')
                    label = edge.get('label', '이유 없음')
                    st.write(f"- **{source}** ➡️ **{target}**: {label}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
