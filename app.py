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

# 3. API 키 가져오기 (보안 강화)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    if not API_KEY or API_KEY == "":
        raise ValueError("API 키가 비어있습니다")
except Exception as e:
    st.error("⚠️ API 키 설정을 확인해주세요.")
    st.info("""
    **API 키 설정 방법:**
    1. Streamlit Cloud: Settings → Secrets에 다음 추가
       ```
       GOOGLE_API_KEY = "your-api-key-here"
       ```
    2. 로컬 실행: `.streamlit/secrets.toml` 파일 생성 후 동일하게 작성
    
    ⚠️ **중요**: API 키를 코드에 직접 입력하지 마세요!
    """)
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
    <div style='background-color: #ffffff; color: #000000; padding: 18px; border-radius: 16px; width: 340px; box-shadow: 0 15px 40px rgba(0,0,0,0.25); border: 2px solid #e0e0e0; font-family: "Noto Sans KR", sans-serif; text-align: left;'>
        <div style='margin-bottom: 12px;'>
            <span style='background-color: {badge_bg}; color: #ffffff; font-size: 11px; font-weight: 800; padding: 5px 10px; border-radius: 6px; letter-spacing: 0.5px;'>{badge_text}</span>
        </div>
        <h3 style='margin: 0 0 6px 0; font-size: 20px; font-weight: 800; color: #000000; line-height: 1.3;'>{book_title_safe}</h3>
        <p style='margin: 0 0 16px 0; font-size: 14px; color: #666666; font-weight: 500;'>👤 {author}</p>
        
        <div style='background-color: #f0f4ff; padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid {badge_bg};'>
            <p style='margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #333333; letter-spacing: 0.5px;'>💡 추천 이유</p>
            <p style='margin: 0; font-size: 13px; line-height: 1.6; color: #000000; font-weight: 500;'>{reason}</p>
        </div>
        
        <div style='background-color: #f8f9fa; padding: 12px; border-radius: 10px; border-left: 5px solid #cccccc;'>
            <p style='margin: 0 0 6px 0; font-size: 12px; font-weight: 800; color: #333333; letter-spacing: 0.5px;'>📖 줄거리</p>
            <p style='margin: 0; font-size: 13px; line-height: 1.6; color: #000000; font-weight: 400;'>{summary}</p>
        </div>
    </div>
    """
    return tooltip_html.replace("\n", "").replace("\r", "").strip()

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

# 7. 그래프 생성 로직 (🔥 더 명확한 프롬프트)
@st.cache_data(ttl=3600)  # 1시간 캐싱
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [임무]
    이 3권의 책을 기반으로 네트워크 그래프용 데이터를 생성하세요.
    
    [규칙]
    1. 입력받은 3권은 "Seed" 그룹으로 지정
    2. 각 Seed 책마다 3-4권의 유사한 책을 "Recommended" 그룹으로 추천
    3. 추가로 2-3권의 심화 책을 "Level2" 그룹으로 추천
    4. 총 15-18개 노드 생성
    5. **중요**: 모든 추천 책은 반드시 하나 이상의 Seed 책과 연결되어야 함
    6. edges의 source와 target은 반드시 nodes에 있는 id와 정확히 일치해야 함
    7. edge label은 연결 이유를 2-4단어로 표현 (예: "실존주의 철학", "성장과 고독", "디스토피아")
    8. **summary**: 각 책의 핵심 줄거리를 2-3문장으로 작성
    9. **reason**: 왜 이 책을 추천하는지 구체적인 이유를 2-3문장으로 작성 (문체, 주제, 분위기 등)
    
    [JSON 형식 - 이 형식만 출력]
    {{
      "nodes": [
        {{"id": "데미안", "title": "데미안", "author": "헤르만 헤세", "group": "Seed", 
          "summary": "한 소년의 성장 과정을 그린 소설로, 자아 발견의 여정을 담고 있습니다.", 
          "reason": "입력하신 책입니다. 성장과 자아 탐구의 고전입니다."}},
        {{"id": "수레바퀴 아래서", "title": "수레바퀴 아래서", "author": "헤르만 헤세", "group": "Recommended", 
          "summary": "천재 소년의 비극적 몰락을 그린 성장소설입니다.", 
          "reason": "데미안과 같은 작가의 작품으로, 교육 시스템 속 개인의 고독을 다룹니다."}}
      ],
      "edges": [
        {{"source": "데미안", "target": "수레바퀴 아래서", "label": "성장과 고독"}},
        {{"source": "데미안", "target": "차라투스트라는 이렇게 말했다", "label": "니체 철학"}}
      ]
    }}
    
    주의: 반드시 유효한 JSON만 출력하고, 설명이나 마크다운은 포함하지 마세요.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        # 429 에러 처리
        if response.status_code == 429:
            st.error("⏳ API 요청 한도 초과 (429 에러)")
            st.info("""
            **대기 시간 안내:**
            - 분당 한도 초과: 1-2분 후 재시도
            - 일일 한도 초과: 내일 다시 시도
            
            💡 **팁**: Google AI Studio에서 API 키 사용량을 확인할 수 있습니다.
            """)
            return None
            
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            raw_text = result['candidates'][0]['content']['parts'][0]['text']
            cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = extract_json(cleaned_text)
            
            # 🔥 디버깅 정보 출력
            if data:
                st.write(f"✅ 노드 개수: {len(data.get('nodes', []))}")
                st.write(f"✅ 엣지 개수: {len(data.get('edges', []))}")
                
                # ID 매칭 검증
                node_ids = {n.get('id') for n in data.get('nodes', [])}
                for edge in data.get('edges', []):
                    src = edge.get('source')
                    tgt = edge.get('target')
                    if src not in node_ids:
                        st.warning(f"⚠️ 엣지 소스 '{src}'가 노드에 없습니다")
                    if tgt not in node_ids:
                        st.warning(f"⚠️ 엣지 타겟 '{tgt}'가 노드에 없습니다")
            
            return data
        else:
            return None
    except Exception as e:
        st.error(f"통신 오류: {e}")
        return None

# 8. Pyvis 시각화 (🔥 노드 간격 대폭 증가)
def visualize_network(data):
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None
    
    # 🔥 물리 엔진 설정 개선: 노드 간격 3배 증가
    options = """
    {
      "nodes": {
        "font": { 
          "size": 16, 
          "face": "Noto Sans KR", 
          "color": "#000000", 
          "strokeWidth": 3, 
          "strokeColor": "#ffffff",
          "bold": true
        },
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "shadow": {
          "enabled": true,
          "size": 10
        }
      },
      "edges": {
        "color": { "color": "#666666", "inherit": false },
        "width": 2,
        "smooth": { 
          "type": "continuous",
          "roundness": 0.5
        },
        "font": {
          "size": 12,
          "face": "Noto Sans KR",
          "align": "middle",
          "background": "#ffffff",
          "strokeWidth": 0,
          "bold": true
        },
        "arrows": {
          "to": {
            "enabled": false
          }
        }
      },
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -200,
          "centralGravity": 0.01,
          "springLength": 350,
          "springConstant": 0.02,
          "damping": 0.7,
          "avoidOverlap": 1
        },
        "stabilization": {
          "enabled": true,
          "iterations": 200
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 50,
        "hideEdgesOnDrag": false,
        "hideEdgesOnZoom": false
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
            size = 50
        elif group == 'Level2':
            color = "#FFD93D"
            size = 25
        else:
            color = "#4ECDC4"
            size = 35
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node_id, 
            label=node_label,
            title=tooltip_html,
            color=color, 
            size=size
        )
    
    # 🔥 엣지 추가 (더 명확한 라벨)
    edge_count = 0
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        label = edge.get('label', '관계')
        
        if source and target:
            net.add_edge(source, target, label=label, title=label)
            edge_count += 1
    
    st.write(f"🔗 생성된 연결선: {edge_count}개")
            
    # CSS 강제 주입
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        custom_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;800&display=swap');
        
        div.vis-tooltip {
            position: fixed !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-family: 'Noto Sans KR', sans-serif !important;
            pointer-events: none !important;
            z-index: 9999 !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        canvas {
            outline: none !important;
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
            if not data.get('edges'):
                st.error("❌ AI가 연결선(edges)을 생성하지 못했습니다. 다시 시도해주세요.")
            else:
                final_html = visualize_network(data)
                if final_html:
                    components.html(final_html, height=770)
                    st.success("✅ 분석 완료! 노드를 드래그하거나 줌인/줌아웃 해보세요.")
                else:
                    st.error("시각화 생성 실패")
        else:
            st.error("AI 응답이 없습니다. 잠시 후 다시 시도해주세요.")

elif analyze_btn:
    st.info("👈 왼쪽 사이드바에 인생 책 3권을 입력하고 버튼을 눌러주세요.")
