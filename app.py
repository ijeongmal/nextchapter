import streamlit as st
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components
import re
import html

# 1. 페이지 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
/* 스트림릿 상단 여백 제거 */
.block-container {
    padding-top: 2rem;
    padding-bottom: 0rem;
}
</style>
""", unsafe_allow_html=True)

# 2. 제목 및 설명
st.title("🌌 AI 도서 취향 탐색기")
st.markdown("세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**를 분석하여 당신만의 독서 우주를 만들어 드립니다.")

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

# 5. 툴팁 HTML 생성 함수 (텍스트 가독성 강제 고정)
def create_tooltip_html(node_data):
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    group = node_data.get('group', 'Recommended')

    # 특수문자 안전 처리
    book_title = html.escape(str(book_title))
    author = html.escape(str(author))
    reason = html.escape(str(reason))
    summary = html.escape(str(summary))

    if group == 'Seed':
        header_bg = "#FF6B6B"
        badge = "SEED BOOK"
    elif group == 'Level2':
        header_bg = "#FFD93D"
        badge = "DEEP DIVE"
    else:
        header_bg = "#4ECDC4"
        badge = "RECOMMENDED"

    # 🌟 [수정] 텍스트 색상을 style='color: white !important;'로 강제
    tooltip_html = f"""
    <div class="book-card" style="color: white !important;">
        <div class="card-header" style="background-color: {header_bg};">
            <span class="badge" style="color: #000000; font-weight: 800;">{badge}</span>
        </div>
        <div class="card-body">
            <h3 style="color: #ffffff !important; margin: 0 0 5px 0;">{book_title}</h3>
            <p style="color: #cccccc !important; margin: 0 0 15px 0; font-size: 13px;">👤 {author}</p>
            
            <div class="section-box" style="border-left: 3px solid {header_bg};">
                <p class="section-title" style="color: #aaaaaa !important;">💡 ANALYSIS (추천 이유)</p>
                <p class="section-content" style="color: #ffffff !important;">{reason}</p>
            </div>
            
            <div class="section-box">
                <p class="section-title" style="color: #aaaaaa !important;">📖 SUMMARY (줄거리)</p>
                <p class="section-content" style="color: #dddddd !important;">{summary}</p>
            </div>
        </div>
    </div>
    """
    return tooltip_html.replace("\n", "").strip()

# 6. JSON 추출 도우미
def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None

# 7. 그래프 생성 로직
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [임무]
    문학 큐레이터로서 책의 정서, 문체, 철학을 연결하여 '꼬리에 꼬리를 무는 추천 지도'를 만드세요.
    
    [단계별 생성]
    1. Seed(입력책) -> Level 1(직접 추천) -> Level 2(파생 추천) 순으로 확장.
    2. 총 노드 15개 이상 필수.
    
    [필수 조건]
    1. 오직 JSON 포맷만 출력. 잡담 금지.
    2. 키 이름: "id", "author", "group", "summary", "reason".
    3. **reason(추천이유)**: "신념과 도덕적 선택의 유사성..." 처럼 핵심 키워드로 시작하여 구체적으로 서술.
    4. **summary(줄거리)**: 책의 핵심 내용 한 줄 요약.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            raw_text = result['candidates'][0]['content']['parts'][0]['text']
            cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
            return extract_json(cleaned_text)
        else:
            return None
    except Exception as e:
        st.error(f"통신 오류: {e}")
        return None

# 8. Pyvis 시각화 (CSS 강제 주입 포함)
def visualize_network(data):
    net = Network(height="750px", width="100%", bgcolor="#0e1117", font_color="white")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None

    # 물리 엔진 설정
    net.force_atlas_2based(
        gravity=-80,
        central_gravity=0.005,
        spring_length=200,
        spring_strength=0.04,
        damping=0.5
    )
    
    for node in data.get('nodes', []):
        if 'id' not in node:
            node['id'] = node.get('title', 'Unknown Book')
            
        group = node.get('group', 'Recommended')
        
        if group == 'Seed':
            color = "#FF6B6B"
            size = 45
        elif group == 'Level2':
            color = "#FFD93D"
            size = 20
        else:
            color = "#4ECDC4"
            size = 30
            
        tooltip_html = create_tooltip_html(node)
        
        # 🌟 노드 추가 시 label 속성 명시 (책 제목이 보이도록)
        net.add_node(
            node['id'], 
            label=str(node['id']),  # 여기가 책 제목 표시 부분
            title=tooltip_html,     # 여기가 마우스 올리면 뜨는 부분
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=4,
            # 폰트 설정 (라벨 색상 흰색 강제)
            font={'face': 'Noto Sans KR', 'size': 16, 'color': 'white', 'strokeWidth': 3, 'strokeColor': '#000000'}
        )
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target, color="rgba(200, 200, 255, 0.2)", width=1)
            
    # 🌟 CSS 강제 주입 (검정 글씨 문제 해결)
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # CSS 스타일: !important를 사용하여 모든 방해 요소를 무시하고 색상 적용
        custom_css = """
        <style>
        /* 기본 툴팁 투명화 및 초기화 */
        div.vis-tooltip {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-family: 'Noto Sans KR', sans-serif !important;
            color: white !important; /* 기본 글자색 흰색 */
        }
        
        /* 카드 디자인 */
        .book-card {
            background-color: #1E222B !important; /* 짙은 남색 배경 */
            color: #ffffff !important; /* 흰색 글자 */
            width: 350px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            border: 1px solid #555;
            backdrop-filter: blur(5px);
            text-align: left;
        }
        
        .card-header {
            padding: 8px 15px;
            display: flex;
            align-items: center;
        }
        
        .card-body {
            padding: 15px;
        }
        
        .section-box {
            background-color: #252A36 !important;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .section-title {
            margin: 0 0 5px 0;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .section-content {
            margin: 0;
            font-size: 13px;
            line-height: 1.5;
        }
        </style>
        """
        
        final_html = html_content.replace('</head>', f'{custom_css}</head>')
        return final_html
        
    except Exception as e:
        st.error(f"HTML 처리 중 오류: {e}")
        return None

# 9. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 당신의 독서 지도를 그리는 중..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            final_html = visualize_network(data)
            if final_html:
                components.html(final_html, height=770)
                st.success("✅ 분석 완료! 노드 위에 마우스를 올려보세요.")
            else:
                st.error("시각화 생성 실패")
        else:
            st.error("AI 응답이 없습니다. 잠시 후 다시 시도해주세요.")

elif analyze_btn:
    st.info("👈 왼쪽 사이드바에 인생 책 3권을 입력하고 버튼을 눌러주세요.")
