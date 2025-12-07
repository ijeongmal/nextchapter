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
    book_title = node_data.get('title') or node_data.get('id') or "제목 없음"
    
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

# 7. 그래프 생성 로직 (🌟 연결선과 라벨 강제 요청)
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [임무]
    책의 정서, 문체, 철학을 연결하여 '추천 지도'를 만드세요.
    
    [필수 조건]
    1. Seed(입력책) -> Level 1(1차 추천) -> Level 2(파생 추천) 순으로 연결.
    2. 총 노드 15개 이상.
    3. 오직 JSON 포맷만 출력.
    4. **Edges(연결선)**: 반드시 노드 간의 연결 관계를 포함해야 함.
    5. **Edge Label(관계 키워드)**: 연결된 두 책 사이의 공통점을 2~4단어의 짧은 키워드로 작성 (예: "부조리 철학 공유", "성장과 고통", "디스토피아적 세계관").
    
    [JSON 구조]
    {{
      "nodes": [
        {{"id": "책제목", "title": "책제목(필수)", "author": "저자", "group": "Seed/Recommended", "summary": "...", "reason": "..."}}
      ],
      "edges": [
        {{"source": "책제목A", "target": "책제목B", "label": "관계 키워드(필수)"}}
      ]
    }}
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

# 8. Pyvis 시각화 (🌟 연결선 라벨 설정 추가)
def visualize_network(data):
    # 배경 흰색
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None
    
    # 🌟 [설정] 연결선 위에 글씨가 잘 보이도록 폰트 설정 추가
    options = """
    {
      "nodes": {
        "font": { "size": 16, "face": "Noto Sans KR", "color": "#000000", "strokeWidth": 3, "strokeColor": "#ffffff" },
        "borderWidth": 2,
        "borderWidthSelected": 4
      },
      "edges": {
        "color": { "color": "#888888", "inherit": false },
        "width": 1.5,
        "smooth": { "type": "continuous" },
        "font": {
          "size": 11,
          "face": "Noto Sans KR",
          "align": "middle",
          "background": "#ffffff",
          "strokeWidth": 0
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.005,
          "springLength": 250,
          "springConstant": 0.04,
          "damping": 0.5
        }
      }
    }
    """
    net.set_options(options)
    
    # 노드 추가
    for node in data.get('nodes', []):
        node_id = node.get('id')
        node_label = node.get('title') or str(node_id)
        
        if not node_id:
            node_id = node_label
            node['id'] = node_id

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
        
        net.add_node(
            node_id, 
            label=node_label,
            title=tooltip_html,
            color=color, 
            size=size
        )
    
    # 🌟 엣지(연결선) 및 라벨(키워드) 추가
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        label = edge.get('label', '') # 관계 키워드 가져오기
        
        if source and target:
            # label 인자에 키워드를 넣으면 선 위에 글씨가 뜹니다
            net.add_edge(source, target, label=label)
            
    # CSS 강제 주입
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
    with st.spinner("AI가 책들의 관계를 연결하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            # 엣지 데이터가 비어있을 경우를 대비한 경고
            if not data.get('edges'):
                st.warning("AI가 책은 찾았으나 연결 관계를 생성하지 못했습니다. 다시 시도해보세요.")
            
            final_html = visualize_network(data)
            if final_html:
                components.html(final_html, height=770)
                st.success("✅ 분석 완료! 선 위의 키워드를 확인해보세요.")
            else:
                st.error("시각화 생성 실패")
        else:
            st.error("AI 응답이 없습니다. 잠시 후 다시 시도해주세요.")

elif analyze_btn:
    st.info("👈 왼쪽 사이드바에 인생 책 3권을 입력하고 버튼을 눌러주세요.")
