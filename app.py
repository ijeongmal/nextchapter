import streamlit as st
import networkx as nx
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components

# 1. 페이지 설정 및 폰트 로드
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 웹 폰트(Noto Sans KR) 강제 적용 및 툴팁 스타일 정의
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 2. 제목 및 설명
st.title("🌌 AI 도서 취향 탐색기")
st.markdown("세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**를 분석하여 당신만의 도서 우주를 만들어 드립니다.")

# 3. API 키 가져오기
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ API 키 설정을 확인해주세요. (Manage app -> Secrets)")
    st.stop()

# 4. 사이드바 입력창
with st.sidebar:
    st.header("📚 나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 참을 수 없는 존재의 가벼움")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 5. HTML 카드 생성 함수 (디자인 핵심)
def create_tooltip_html(node_data):
    # 보내주신 스크린샷과 유사한 '다크 카드' 스타일
    bg_color = "#1E222B"  # 진한 남색 배경
    text_color = "#FFFFFF"
    accent_color = "#4ECDC4" if node_data['group'] == 'Recommended' else "#FF6B6B"
    badge_text = "RECOMMENDED" if node_data['group'] == 'Recommended' else "SEED BOOK"
    
    html = f"""
    <div style="
        font-family: 'Noto Sans KR', sans-serif;
        background-color: {bg_color};
        color: {text_color};
        padding: 20px;
        border-radius: 12px;
        width: 320px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border: 1px solid #333;
        text-align: left;
    ">
        <div style="
            display: inline-block;
            background-color: {accent_color};
            color: #1e1e1e;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            margin-bottom: 10px;
        ">
            {badge_text}
        </div>
        <h3 style="margin: 0 0 5px 0; font-size: 22px; font-weight: 700;">{node_data['id']}</h3>
        <p style="margin: 0 0 15px 0; font-size: 14px; color: #aaaaaa;">👤 {node_data.get('author', '저자 미상')}</p>
        
        <div style="
            background-color: #2C303A;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        ">
            <p style="margin: 0 0 5px 0; font-size: 11px; color: #888; font-weight: bold;">ANALYSIS</p>
            <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #ddd;">
                {node_data.get('reason', '분석 내용이 없습니다.')}
            </p>
        </div>
        
        <p style="margin: 5px 0 0 0; font-size: 12px; color: #666; border-top: 1px solid #444; padding-top: 10px;">
            📖 {node_data.get('summary', '')}
        </p>
    </div>
    """
    return html

# 6. 그래프 생성 로직 (Gemini 2.5 Flash)
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # 프롬프트: 저자(author) 정보 추가 요청
    prompt = f"""
    사용자가 입력한 3권의 책: {books}
    
    [목표]
    이 책들을 기반으로 문체, 철학, 난이도가 유사한 도서 추천 네트워크를 구성해줘.
    
    [출력 조건]
    1. 총 15개 내외의 노드(책)를 구성해.
    2. 각 책마다 다음 정보를 반드시 포함해:
       - title: 책 제목
       - author: 저자 이름 (중요!)
       - reason: 이 책을 추천하는 구체적인 이유 (문체, 철학적 공통점 위주로 서술형으로 작성)
       - summary: 책의 한 줄 요약
       - group: "Seed"(입력한 책) 또는 "Recommended"(추천된 책)
    3. JSON 형식으로만 출력해.
    
    [JSON 예시]
    {{
        "nodes": [
            {{"id": "데미안", "author": "헤르만 헤세", "group": "Seed", "summary": "...", "reason": "..."}},
            {{"id": "이방인", "author": "알베르 카뮈", "group": "Recommended", "summary": "...", "reason": "..."}}
        ],
        "edges": [
            {{"source": "데미안", "target": "이방인"}}
        ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            text = result['candidates'][0]['content']['parts'][0]['text']
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        else:
            return None
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# 7. Pyvis 시각화 및 물리 엔진 설정
def visualize_network(data):
    # 배경색을 어두운 테마에 맞게 조정 (Streamlit과 어울리게)
    net = Network(height="650px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 🌟 물리 엔진 설정: '둥실둥실'한 느낌 (Force Atlas 2 Based)
    # gravity가 낮을수록 더 넓게 퍼지고, springLength가 길수록 둥실거림
    net.force_atlas_2based(
        gravity=-50,           # 서로 밀어내는 힘 (음수일수록 강함)
        central_gravity=0.01,  # 중앙으로 당기는 힘 (낮을수록 퍼짐)
        spring_length=150,     # 엣지의 길이 (길수록 여유로움)
        spring_strength=0.08,  # 스프링의 탄성
        damping=0.4            # 멈추는 속도 (낮을수록 계속 움직임)
    )
    
    # 노드 추가
    for node in data.get('nodes', []):
        if node['group'] == 'Seed':
            color = "#FF6B6B" # 코랄 핑크
            size = 30
        else:
            color = "#4ECDC4" # 민트
            size = 20
            
        # 🌟 HTML 카드를 title 속성에 삽입 (마우스 오버/클릭 시 뜸)
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_html, # 여기에 HTML 카드가 들어감
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=4
        )
    
    # 엣지 추가
    for edge in data.get('edges', []):
        net.add_edge(edge['source'], edge['target'], color="rgba(200, 200, 200, 0.3)")
    
    return net

# 8. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 책들의 우주를 연결하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            net = visualize_network(data)
            
            # HTML 파일로 저장 후 표시
            try:
                path = "tmp_network.html"
                net.save_graph(path)
                
                with open(path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                # HTML 렌더링
                components.html(source_code, height=670)
                
                st.success("네트워크 생성 완료! 노드에 마우스를 올려보세요.")
                
            except Exception as e:
                st.error(f"시각화 중 오류가 발생했습니다: {e}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
