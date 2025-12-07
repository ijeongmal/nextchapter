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
.block-container {
    padding-top: 2rem;
    padding-bottom: 0rem;
}
</style>
""", unsafe_allow_html=True)

# 2. 제목 및 설명
st.title("🌌 AI 도서 취향 탐색기")
st.markdown("세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**등을 분석하여 당신만의 독서 우주를 만들어 드립니다.")

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

# 5. 툴팁 HTML 생성 함수 (오류 원천 차단)
def create_tooltip_html(node_data):
    # 데이터 가져오기
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    group = node_data.get('group', 'Recommended')

    # 🌟 [핵심 수정] HTML을 깨뜨리는 따옴표(')를 HTML 엔티티(&#39;)로 강제 변환
    # 이 과정이 없으면 툴팁이 코드로 보입니다.
    def clean_text(text):
        if not text: return ""
        return html.escape(str(text)).replace("'", "&#39;").replace('"', "&quot;")

    book_title = clean_text(book_title)
    author = clean_text(author)
    reason = clean_text(reason)
    summary = clean_text(summary)

    if group == 'Seed':
        badge_color = "#FF6B6B" # 코랄
        badge_text = "SEED BOOK"
    elif group == 'Level2':
        badge_color = "#FFD93D" # 노랑
        badge_text = "DEEP DIVE"
    else:
        badge_color = "#4ECDC4" # 민트
        badge_text = "RECOMMENDED"

    # 🌟 HTML 구조 단순화 (인라인 스타일 최소화 -> CSS 클래스 의존)
    tooltip_html = f"""
    <div class="book-card">
        <div class="card-header">
            <span class="badge" style="background-color: {badge_color};">{badge_text}</span>
        </div>
        <div class="card-body">
            <h3>{book_title}</h3>
            <p class="author">👤 {author}</p>
            <div class="section-box reason">
                <p class="section-title">💡 Analysis</p>
                <p class="section-content">{reason}</p>
            </div>
            <div class="section-box summary">
                <p class="section-title">📖 Summary</p>
                <p class="section-content">{summary}</p>
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
    
    [필수 조건]
    1. 오직 JSON 포맷만 출력.
    2. 키 이름: "id", "author", "group", "summary", "reason".
    3. **reason(추천이유)**: 반드시 "OOO와 유사한 신념) 구체적 내용" 형식으로 작성할 것.
       예시: "전체주의에 대한 비판적 시각 공유) 1984에서 느꼈던 통제 사회의 공포가 이 책에서는..."
    4. **summary(줄거리)**: 책의 핵심 내용을 1~2문장으로 요약.
    5. 노드 개수: 최소 15개 이상.
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

# 8. Pyvis 시각화 (화이트 테마 + 검정 글씨)
def visualize_network(data):
    # 배경 흰색, 글자 검정
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None

    # 물리 엔진
    net.force_atlas_2based(
        gravity=-60,
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
            color = "#FF6B6B" # 코랄 (진하게)
            size = 45
        elif group == 'Level2':
            color = "#FFD93D" # 노랑
            size = 20
        else:
            color = "#4ECDC4" # 민트
            size = 30
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=str(node['id']),
            title=tooltip_html,
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=4,
            # 라벨: 검정색 글씨, 흰색 테두리 (가독성 확보)
            font={'face': 'Noto Sans KR', 'size': 16, 'color': 'black', 'strokeWidth': 4, 'strokeColor': '#ffffff'}
        )
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            # 연결선: 진한 회색 (흰 배경에서 잘 보임)
            net.add_edge(source, target, color="#888888", width=1.5)
            
    # 🌟 CSS 강제 주입 (카드를 예쁘게 만드는 마법)
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        custom_css = """
        <style>
        /* 기본 툴팁 제거 */
        div.vis-tooltip {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-family: 'Noto Sans KR', sans-serif !important;
            color: black !important;
        }
        
        /* 화이트 카드 디자인 */
        .book-card {
            background-color: #ffffff !important;
            color: #000000 !important;
            width: 320px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 30px rgba(0,0,0,0.15); /* 부드러운 그림자 */
            border: 1px solid #e0e0e0;
            text-align: left;
            font-family: 'Noto Sans KR', sans-serif;
        }
        
        .card-header {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            background-color: #fafafa;
        }
        
        .badge {
            color: #000000;
            font-size: 11px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        
        .card-body {
            padding: 15px;
        }
        
        .card-body h3 {
            margin: 0 0 5px 0;
            font-size: 18px;
            font-weight: 700;
            color: #111111 !important;
        }
        
        .author {
            margin: 0 0 15px 0;
            font-size: 13px;
            color: #666666 !important;
        }
        
        .section-box {
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        
        .reason {
            background-color: #f0f7ff; /* 연한 파랑 배경 */
            border-left: 3px solid #007bff;
        }
        
        .summary {
            background-color: #f9f9f9; /* 연한 회색 배경 */
            border-left: 3px solid #ccc;
        }
        
        .section-title {
            margin: 0 0 4px 0;
            font-size: 11px;
            font-weight: bold;
            color: #555555 !important;
            text-transform: uppercase;
        }
        
        .section-content {
            margin: 0;
            font-size: 12.5px;
            line-height: 1.5;
            color: #222222 !important;
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
    with st.spinner("Nextchapter가 당신만의 독서 지도를 그리는 중입니다..."):
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
