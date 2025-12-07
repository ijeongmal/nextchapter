import streamlit as st
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components
import re
import html  # 🌟 텍스트 깨짐 방지용 도구 추가

# 1. 페이지 설정 및 폰트 로드
st.set_page_config(page_title="Literary Nexus", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
/* 스트림릿 기본 여백 제거 */
.block-container {
    padding-top: 2rem;
    padding-bottom: 0rem;
}
</style>
""", unsafe_allow_html=True)

# 2. 제목 및 설명
st.title("🌌 AI 도서 취향 탐색기")
st.markdown("세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**를 분석하여 당신만의 독서 지도를 만들어 드립니다.")

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

# 5. 툴팁 HTML 생성 함수 (🌟 텍스트 안전 처리 강화)
def create_tooltip_html(node_data):
    # 데이터 가져오기 (없으면 기본값)
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '상세 분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    group = node_data.get('group', 'Recommended')

    # 🌟 [핵심] HTML을 깨뜨리는 특수문자(<, >, ", ')를 안전하게 변환
    book_title_safe = html.escape(book_title)
    author_safe = html.escape(author)
    reason_safe = html.escape(reason)
    summary_safe = html.escape(summary)

    # 그룹별 색상
    if group == 'Seed':
        header_color = "#FF6B6B" # 코랄
        badge = "SEED BOOK"
    elif group == 'Level2':
        header_color = "#FFD93D" # 노랑
        badge = "DEEP DIVE"
    else:
        header_color = "#4ECDC4" # 민트
        badge = "RECOMMENDED"

    # 🌟 깔끔한 카드 디자인 HTML
    tooltip_html = f"""
    <div class="book-card">
        <div class="card-header" style="background-color: {header_color};">
            <span class="badge">{badge}</span>
        </div>
        <div class="card-body">
            <h3>{book_title_safe}</h3>
            <p class="author">👤 {author_safe}</p>
            <div class="reason-box" style="border-left: 3px solid {header_color};">
                <p class="label">💡 추천 이유</p>
                <p class="content">{reason_safe}</p>
            </div>
            <div class="summary-box">
                <p>📖 {summary_safe}</p>
            </div>
        </div>
    </div>
    """
    # 줄바꿈 제거하여 한 줄로 만듦 (JS 오류 방지)
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
    2. 키 이름 준수: "id", "author", "group"("Seed", "Recommended", "Level2"), "summary", "reason".
    3. 추천 이유(reason)는 구체적이고 감성적으로 2~3문장 작성.
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

# 8. Pyvis 시각화 및 커스텀 디자인 주입
def visualize_network(data):
    # 높이를 넉넉하게 설정
    net = Network(height="750px", width="100%", bgcolor="#0e1117", font_color="white")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None

    # 🌟 물리 엔진 설정 (부드러운 움직임)
    net.force_atlas_2based(
        gravity=-80,
        central_gravity=0.005,
        spring_length=200,
        spring_strength=0.04,
        damping=0.5
    )
    
    # 노드 추가
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
            
        # 툴팁 HTML 생성
        tooltip_content = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_content, # 여기가 마우스 올리면 뜨는 내용
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=4,
            font={'face': 'Noto Sans KR', 'size': 16, 'color': 'white', 'strokeWidth': 3, 'strokeColor': '#000000'}
        )
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target, color="rgba(200, 200, 255, 0.2)", width=1)
            
    # 🌟 [핵심] 툴팁 디자인을 위한 커스텀 CSS 주입
    # Pyvis가 만든 HTML 파일을 저장한 뒤, CSS를 강제로 끼워넣습니다.
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        
        # HTML 파일 읽기
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 🌟 CSS 주사 (툴팁 스타일링)
        # vis-tooltip 클래스가 라이브러리 기본 툴팁입니다. 이걸 우리가 원하는대로 바꿉니다.
        custom_css = """
        <style>
        /* 기본 툴팁 스타일 덮어쓰기 */
        div.vis-tooltip {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-family: 'Noto Sans KR', sans-serif !important;
            overflow: visible !important;
            z-index: 9999 !important;
        }
        
        /* 우리가 만든 카드 스타일 */
        .book-card {
            background-color: #1E222B;
            color: #ffffff;
            width: 320px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.8);
            border: 1px solid #444;
            backdrop-filter: blur(10px);
        }
        .card-header {
            padding: 8px 15px;
            display: flex;
            align-items: center;
        }
        .badge {
            background-color: rgba(0,0,0,0.2);
            color: #1e1e1e;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .card-body {
            padding: 15px;
        }
        .card-body h3 {
            margin: 0 0 5px 0;
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
        }
        .author {
            margin: 0 0 15px 0;
            font-size: 13px;
            color: #aaaaaa;
        }
        .reason-box {
            background-color: #2C303A;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        .label {
            margin: 0 0 4px 0;
            font-size: 11px;
            color: #999;
            font-weight: bold;
        }
        .content {
            margin: 0;
            font-size: 13px;
            line-height: 1.5;
            color: #eee;
        }
        .summary-box {
            border-top: 1px solid #444;
            padding-top: 10px;
            font-size: 12px;
            color: #888;
            line-height: 1.4;
        }
        </style>
        """
        
        # 헤드 태그 안에 CSS 삽입
        final_html = html_content.replace('</head>', f'{custom_css}</head>')
        
        return final_html
        
    except Exception as e:
        st.error(f"HTML 처리 중 오류: {e}")
        return None

# 9. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 독서 지도를 그리고 있습니다..."):
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
