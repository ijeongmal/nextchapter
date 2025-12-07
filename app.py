import streamlit as st
import networkx as nx
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components
import re

# 1. 페이지 설정 및 폰트 로드
st.set_page_config(page_title="Literary Nexus", layout="wide")

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
st.markdown("세 권의 책을 입력하면, **작가의 문체, 철학, 분위기**를 분석하여 **꼬리에 꼬리를 무는 도서 우주**를 만들어 드립니다.")

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

# 5. HTML 카드 생성 함수 (오류 방지 강화)
def create_tooltip_html(node_data):
    bg_color = "#1E222B"
    text_color = "#FFFFFF"
    
    group = node_data.get('group', 'Recommended')
    # 그룹에 따라 뱃지 색상 및 텍스트 변경
    if group == 'Seed':
        accent_color = "#FF6B6B" # 코랄
        badge_text = "SEED BOOK"
    elif group == 'Level2':
        accent_color = "#FFD93D" # 노랑 (심화 추천)
        badge_text = "DEEP DIVE"
    else:
        accent_color = "#4ECDC4" # 민트 (1차 추천)
        badge_text = "RECOMMENDED"
    
    # 데이터 가져오기 (없으면 기본값)
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    
    # 🌟 [중요] 텍스트 내의 따옴표(")가 HTML을 깨뜨리지 않도록 변환
    reason = reason.replace('"', "'")
    summary = summary.replace('"', "'")
    
    html = f"""
    <div style="font-family: 'Noto Sans KR', sans-serif; background-color: {bg_color}; color: {text_color}; padding: 15px; border-radius: 12px; width: 320px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); border: 1px solid #444; text-align: left;">
        <div style="display: inline-block; background-color: {accent_color}; color: #1e1e1e; font-size: 10px; font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px;">
            {badge_text}
        </div>
        <h3 style="margin: 0 0 5px 0; font-size: 19px; font-weight: 700; color: white;">{book_title}</h3>
        <p style="margin: 0 0 12px 0; font-size: 13px; color: #aaaaaa;">👤 {author}</p>
        <div style="background-color: #2C303A; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {accent_color};">
            <p style="margin: 0 0 5px 0; font-size: 11px; color: #999; font-weight: bold;">💡 추천 이유</p>
            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #eee;">{reason}</p>
        </div>
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #888; border-top: 1px solid #444; padding-top: 8px;">📖 {summary}</p>
    </div>
    """
    # 줄바꿈 제거 (브라우저 인식용)
    return html.replace("\n", "")

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

# 7. 그래프 생성 로직 (프롬프트 대폭 수정: 꼬리물기 구조 강제)
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권(Seed Books): {books}
    
    [당신의 임무]
    당신은 심층적인 문학 큐레이터입니다. 단순한 베스트셀러 추천이 아니라, 책의 '정서', '문체', '철학'을 연결고리로 하여 **꼬리에 꼬리를 무는 확장형 추천망**을 만들어야 합니다.
    
    [생성 규칙 - 반드시 단계별로 수행]
    1. **Level 0 (Seed)**: 입력받은 3권의 책.
    2. **Level 1 (Direct Recs)**: 각 Seed Book마다, 취향이 비슷한 책을 2~3권씩 추천합니다. (총 6~9권)
    3. **Level 2 (Deep Recs)**: 위에서 추천한 Level 1 책들 중 일부에 대해, 또다시 연관된 책을 1~2권씩 파생 추천합니다. (총 5~8권) -> **이 부분이 "추천책의 추천책"입니다.**
    4. **Connection**: 
       - Seed -> Level 1 연결
       - Level 1 -> Level 2 연결
       - 서로 다른 그룹 간에도 취향이 겹치면 연결 (Cross-link)
    
    [출력 포맷 조건]
    1. 오직 JSON 형식으로만 출력하십시오. (마크다운 ``` 사용 금지)
    2. 총 노드(책) 개수는 **최소 15개 이상**이어야 합니다.
    3. **추천 이유(reason)**는 "이 작가의 건조한 문체를 좋아한다면..." 처럼 **아주 구체적이고 3문장 이상**으로 길게 작성하십시오.
    
    [JSON 구조 예시]
    {{
      "nodes": [
        {{"id": "데미안", "author": "헤르만 헤세", "group": "Seed", "summary": "...", "reason": "사용자 입력 도서"}},
        {{"id": "이방인", "author": "알베르 카뮈", "group": "Recommended", "summary": "...", "reason": "데미안의 자아 탐구와 유사한..."}},
        {{"id": "페스트", "author": "알베르 카뮈", "group": "Level2", "summary": "...", "reason": "이방인에서 보여준 부조리 의식이 공동체로 확장된..."}}
      ],
      "edges": [
        {{"source": "데미안", "target": "이방인"}},
        {{"source": "이방인", "target": "페스트"}}
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

# 8. Pyvis 시각화 함수
def visualize_network(data):
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 리스트 처리 및 검증
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
    if not isinstance(data, dict) or 'nodes' not in data:
        return None

    # 🌟 물리 엔진: 더 넓고 웅장하게 퍼지도록 설정
    net.force_atlas_2based(
        gravity=-100,          # 서로 강하게 밀어냄
        central_gravity=0.005, # 중앙 인력 최소화 (넓게 퍼짐)
        spring_length=250,     # 연결선 길이 대폭 증가
        spring_strength=0.03,  # 아주 유연한 움직임
        damping=0.4
    )
    
    # 노드 추가
    for node in data.get('nodes', []):
        if 'id' not in node:
            node['id'] = node.get('title', 'Unknown Book')
            
        group = node.get('group', 'Recommended')
        
        # 그룹별 디자인 차별화
        if group == 'Seed':
            color = "#FF6B6B" # 메인 (빨강)
            size = 45
        elif group == 'Level2':
            color = "#FFD93D" # 심화 추천 (노랑)
            size = 20
        else:
            color = "#4ECDC4" # 1차 추천 (민트)
            size = 30
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_html,
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=5,
            font={'face': 'Noto Sans KR', 'size': 16, 'color': 'white', 'strokeWidth': 2, 'strokeColor': '#000000'}
        )
    
    # 엣지 추가
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target, color="rgba(200, 200, 255, 0.2)", width=1)
    
    return net

# 9. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 꼬리에 꼬리를 무는 독서 지도를 그리고 있습니다... (약 10초 소요)"):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            try:
                net = visualize_network(data)
                if net:
                    path = "tmp_network.html"
                    net.save_graph(path)
                    with open(path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    components.html(source_code, height=720)
                    st.success("✅ 분석 완료! 노드 위에 마우스를 올려 추천 이유를 확인하세요.")
                else:
                    st.error("데이터 생성 실패: AI가 유효한 그래프를 만들지 못했습니다.")
            except Exception as e:
                st.error(f"시각화 오류: {e}")
        else:
            st.error("AI 응답이 없습니다. 잠시 후 다시 시도해주세요.")

elif analyze_btn:
    st.info("👈 왼쪽 사이드바에 인생 책 3권을 입력하고 버튼을 눌러주세요.")
