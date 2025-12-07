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

# 5. 툴팁 HTML 생성 함수
def create_tooltip_html(node_data):
    # 🌟 [수정] id보다 title을 우선적으로 가져오도록 변경
    # AI가 id에 "1", "A" 같은 걸 넣고 title에 진짜 제목을 넣을 때를 대비
    book_title = node_data.get('title') or node_data.get('id') or "제목 없음"
    
    # 텍스트 안전 처리
    def clean(text):
        if not text: return ""
        return html.escape(str(text)).replace("'", "&#39;").replace('"', "&quot;")

    book_title_safe = clean(book_title)
    author = clean(node_data.get('author', '저자 미상'))
    reason = clean(node_data.get('reason', '분석 내용이 없습니다.'))
    summary = clean(node_data.get('summary', '줄거리 정보가 없습니다.'))
    group = node_data.get('group', 'Recommended')

    if group == 'Seed':
        badge_bg = "#FF6B6B"
        badge_text = "SEED BOOK"
    elif group == 'Level2':
        badge_bg = "#FFD93D"
        badge_text = "DEEP DIVE"
    else:
        badge_bg = "#4ECDC4"
        badge_text = "RECOMMENDED"

    tooltip_html = f"""
    <div style='background-color: #ffffff; color: #000000; padding: 15px; border-radius: 12px; width: 320px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); border: 1px solid #e0e0e0; font-family: "Noto Sans KR", sans-serif; text-align: left;'>
        <div style='margin-bottom: 10px;'>
            <span style='background-color: {badge_bg}; color: #000000; font-size: 10px; font-weight: 800; padding: 4px 8px; border-radius: 4px;'>{badge_text}</span>
        </div>
        <h3 style='margin: 0 0 5px 0; font-size: 18px; font-weight: 700; color: #000000;'>{book_title_safe}</h3>
        <p style='margin: 0 0 15px 0; font-size: 13px; color: #666666;'>👤 {author}</p>
        
        <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {badge_bg};'>
            <p style='margin: 0 0 4px 0; font-size: 11px; font-weight: bold; color: #555555;'>💡 ANALYSIS</p>
            <p style='margin: 0; font-size: 12px; line-height: 1.5; color: #222222;'>{reason}</p>
        </div>
        
        <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 4px solid #cccccc;'>
            <p style='margin: 0 0 4px 0; font-size: 11px; font-weight: bold; color: #555555;'>📖 SUMMARY</p>
            <p style='margin: 0; font-size: 12px; line-height: 1.5; color: #222222;'>{summary}</p>
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
    
    [조건]
    1. Seed(입력책) -> Level 1(1차 추천) -> Level 2(파생 추천) 순으로 확장.
    2. 총 노드 15개 이상.
    3. 오직 JSON 포맷만 출력.
    4. 키 이름: "id", "title" (책제목 필수), "author", "group", "summary", "reason".
    5. **중요**: "id"는 고유 식별자(숫자나 문자)여도 되지만, **"title"** 키에 반드시 책 제목을 한글로 정확히 적으세요.
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

# 8. Pyvis 시각화
def visualize_network(data):
    # 🌟 [설정] 배경 흰색(#ffffff), 기본 글자 검정(#000000)
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None
    
    # 🌟 [핵심] 전체 옵션 설정 (여기서 선 색상을 강제합니다)
    # edges: color를 진한 회색(#666666)으로 고정
    # physics: 둥실둥실 효과
    options = """
    {
      "nodes": {
        "font": {
          "size": 16,
          "face": "Noto Sans KR",
          "color": "#000000",
          "strokeWidth": 3,
          "strokeColor": "#ffffff"
        },
        "borderWidth": 2,
        "borderWidthSelected": 4
      },
      "edges": {
        "color": {
          "color": "#666666",
          "highlight": "#000000",
          "hover": "#000000"
        },
        "width": 1.5,
        "smooth": {
          "type": "continuous"
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "centralGravity": 0.005,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.5
        },
        "solver": "forceAtlas2Based"
      }
    }
    """
    net.set_options(options)
    
    for node in data.get('nodes', []):
        # ID와 Title 처리 (가장 중요한 수정)
        node_id = node.get('id')
        # 라벨(화면에 뜨는 글자)은 title이 있으면 title, 없으면 id 사용
        node_label = node.get('title') or str(node_id)
        
        # ID가 없으면 에러나므로 임의 지정
        if not node_id:
            node_id = node_label
            node['id'] = node_id

        group = node.get('group', 'Recommended')
        
        if group == 'Seed':
            color = "#FF6B6B" # 코랄
            size = 45
        elif group == 'Level2':
            color = "#FFD93D" # 노랑
            size = 20
        else:
            color = "#4ECDC4" # 민트
            size = 30
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node_id, 
            label=node_label, # 🌟 여기가 'A' '1' 대신 '책제목'이 뜨게 하는 핵심
            title=tooltip_html,
            color=color, 
            size=size
        )
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target)
            
    # CSS 강제 주입 (툴팁 초기화)
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        custom_css = """
        <style>
        div.vis-tooltip {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-family: 'Noto Sans KR', sans-serif !important;
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
    with st.spinner("AI가 꼬리에 꼬리를 무는 독서 지도를 그리는 중..."):
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
