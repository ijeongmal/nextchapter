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
st.title("🌌 NextChapter")

# [중요] 여기서 변수(상자)를 먼저 만들어야 합니다!
desc_placeholder = st.empty() 

# 만든 상자 안에 글씨 넣기
desc_placeholder.markdown(
    """
    세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**등을 분석하여 당신만의 독서 지도를 만들어 드립니다.<br><br>
    👈 왼쪽 사이드바에 책 3권을 입력하고 버튼을 눌러주세요.
    """, 
    unsafe_allow_html=True
)

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
    st.header("📚 책 제목")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 참을 수 없는 존재의 가벼움")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 5. 간단한 텍스트 툴팁 생성 (HTML 제거)
def create_tooltip_text(node_data):
    """HTML 없이 순수 텍스트로만 툴팁 생성"""
    book_title = node_data.get('title') or node_data.get('id') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '추천 이유가 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    group = node_data.get('group', 'Recommended')
    
    if group == 'Seed':
        badge = "🔴 입력한 책"
    elif group == 'Level2':
        badge = "🟡 심화 추천"
    else:
        badge = "🔵 추천 도서"
    
    # 순수 텍스트로만 구성
    tooltip = f"{badge}\n\n📚 {book_title}\n✍️ {author}\n\n💡 추천 이유:\n{reason}\n\n📖 줄거리:\n{summary}"
    
    return tooltip

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

# 7. 그래프 생성 로직 (🔥 재시도 로직 추가)
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
    9. **reason**: 왜 이 책을 추천하는지 구체적인 이유를 1-2문장으로 간결하게 작성
    
    [JSON 형식 - 이 형식만 출력]
    {{
      "nodes": [
        {{"id": "데미안", "title": "데미안", "author": "헤르만 헤세", "group": "Seed", 
          "summary": "한 소년의 성장 과정을 그린 소설로, 자아 발견의 여정을 담고 있습니다.", 
          "reason": "입력하신 책입니다."}},
        {{"id": "한낮의 어둠", "title": "한낮의 어둠", "author": "아르투어 쾨슬러", "group": "Recommended", 
          "summary": "스탈린 시대의 숙청을 배경으로, 한 혁명가의 고뇌와 이념적 갈등을 그린 정치 소설입니다.", 
          "reason": "전체주의 체제에서의 신념과 도덕적 선택을 다룹니다."}}
      ],
      "edges": [
        {{"source": "데미안", "target": "한낮의 어둠", "label": "신념과 선택"}},
        {{"source": "1984", "target": "한낮의 어둠", "label": "전체주의 비판"}}
      ]
    }}
    
    주의: 반드시 유효한 JSON만 출력하고, 설명이나 마크다운은 포함하지 마세요.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # 🔥 재시도 로직 (최대 3번 시도)
    max_retries = 3
    retry_delays = [2, 5, 10]
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 429:
                st.error("⏳ API 요청 한도 초과 (429 에러)")
                st.info("""
                **대기 시간 안내:**
                - 분당 한도 초과: 1-2분 후 재시도
                - 일일 한도 초과: 내일 다시 시도
                
                💡 **팁**: Google AI Studio에서 API 키 사용량을 확인할 수 있습니다.
                """)
                return None
            
            if response.status_code == 503 and attempt < max_retries - 1:
                st.warning(f"⚠️ 서버 일시 중단. {retry_delays[attempt]}초 후 재시도... ({attempt + 1}/{max_retries})")
                import time
                time.sleep(retry_delays[attempt])
                continue
                
            response.raise_for_status()
            result = response.json()
            
            if 'candidates' in result and result['candidates']:
                raw_text = result['candidates'][0]['content']['parts'][0]['text']
                cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
                data = extract_json(cleaned_text)
                
                # 데이터 검증 (화면에 표시하지 않음)
                if data:
                    node_ids = {n.get('id') for n in data.get('nodes', [])}
                    for edge in data.get('edges', []):
                        src = edge.get('source')
                        tgt = edge.get('target')
                        # 검증만 하고 출력은 하지 않음
                        pass
                
                return data
            else:
                return None
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                st.warning(f"⏱️ 응답 시간 초과. {retry_delays[attempt]}초 후 재시도... ({attempt + 1}/{max_retries})")
                import time
                time.sleep(retry_delays[attempt])
            else:
                st.error("""
                ❌ **API 응답 시간 초과**
                
                **해결 방법:**
                1. 잠시 후 다시 시도해주세요
                2. Google Gemini API 서버가 일시적으로 느릴 수 있습니다
                3. 네트워크 연결 상태를 확인해주세요
                """)
                return None
                
        except requests.exceptions.ConnectionError:
            st.error("❌ 네트워크 연결 오류. 인터넷 연결을 확인하고 다시 시도해주세요.")
            return None
            
        except Exception as e:
            if attempt < max_retries - 1:
                st.warning(f"⚠️ 오류 발생: {str(e)[:100]}. 재시도 중...")
                import time
                time.sleep(retry_delays[attempt])
            else:
                st.error(f"❌ 통신 오류: {e}")
                return None
    
    return None

# 8. Pyvis 시각화 + 커스텀 툴팁
def visualize_network(data):
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000")
    
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None
    
    # 물리 엔진 설정
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
            
        tooltip_text = create_tooltip_text(node)
        
        net.add_node(
            node_id, 
            label=node_label,
            title=tooltip_text,  # 텍스트만 전달
            color=color, 
            size=size
        )
    
    # 엣지 추가
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        label = edge.get('label', '관계')
        
        if source and target:
            net.add_edge(source, target, label=label, title=label)
            
    # HTML 생성 및 커스텀 CSS 추가
    try:
        path = "tmp_network.html"
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 🎨 커스텀 툴팁 스타일
        custom_style = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap');
        
        div.vis-tooltip {
            font-family: 'Noto Sans KR', sans-serif !important;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
            color: #000000 !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 16px !important;
            padding: 20px !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15) !important;
            max-width: 380px !important;
            font-size: 14px !important;
            line-height: 1.7 !important;
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            z-index: 999999 !important;
            pointer-events: none !important;
        }
        
        canvas {
            outline: none !important;
        }
        </style>
        """
        
        final_html = html_content.replace('</head>', f'{custom_style}</head>')
        return final_html
        
    except Exception as e:
        st.error(f"HTML 처리 중 오류: {e}")
        return None


# 9. 메인 실행
if analyze_btn and book1 and book2 and book3:
    # 위에서 만든 상자를 비움 (이 줄에서 에러가 났던 것임)
    desc_placeholder.empty() 

    # 안내 멘트용 새 상자 생성
    msg_placeholder = st.empty()
    msg_placeholder.markdown(
        """
        <div style="text-align: left; margin-bottom: 15px;">
            <strong>Nextchapter가 책들의 우주를 연결하고 있습니다... 🚀</strong><br>
            추천 네트워크 생성을 위해 약간의 시간이 필요합니다.<br>
            잠시만 기다려 주세요.
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. 스피너와 함께 분석 시작
    with st.spinner("AI 분석 진행 중..."):
        data = get_recommendations([book1, book2, book3])
    
    # 3. 분석이 끝나면 로딩 멘트도 지움
    msg_placeholder.empty()

    # 4. 결과 출력
    if data:
        if not data.get('edges'):
            st.error("❌ AI가 연결선(edges)을 생성하지 못했습니다. 다시 시도해주세요.")
        else:
            final_html = visualize_network(data)
            if final_html:
                components.html(final_html, height=770)
                st.success("✅ 분석 완료! 노드에 마우스를 올려보세요 📚")
            else:
                st.error("시각화 생성 실패")
    else:
        st.error("AI 응답이 없습니다. 잠시 후 다시 시도해주세요.")
