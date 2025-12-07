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

# 5. HTML 카드 생성 함수
def create_tooltip_html(node_data):
    bg_color = "#1E222B"
    text_color = "#FFFFFF"
    
    group = node_data.get('group', 'Recommended')
    accent_color = "#4ECDC4" if group == 'Recommended' else "#FF6B6B"
    badge_text = "RECOMMENDED" if group == 'Recommended' else "SEED BOOK"
    
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '상세 분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    
    html = f"""
    <div style="font-family: 'Noto Sans KR', sans-serif; background-color: {bg_color}; color: {text_color}; padding: 15px; border-radius: 12px; width: 300px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #333; text-align: left;">
        <div style="display: inline-block; background-color: {accent_color}; color: #1e1e1e; font-size: 10px; font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-bottom: 8px;">
            {badge_text}
        </div>
        <h3 style="margin: 0 0 5px 0; font-size: 18px; font-weight: 700; color: white;">{book_title}</h3>
        <p style="margin: 0 0 12px 0; font-size: 13px; color: #aaaaaa;">👤 {author}</p>
        <div style="background-color: #2C303A; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {accent_color};">
            <p style="margin: 0 0 5px 0; font-size: 11px; color: #888; font-weight: bold;">💡 추천 이유</p>
            <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #eee;">{reason}</p>
        </div>
        <p style="margin: 8px 0 0 0; font-size: 11px; color: #777; border-top: 1px solid #444; padding-top: 8px;">📖 {summary}</p>
    </div>
    """
    return html.replace("\n", "")

# 6. JSON 추출 도우미 함수
def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    try:
        # 중괄호 { } 또는 대괄호 [ ] 패턴 찾기
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except Exception:
        pass
        
    return None

# 7. 그래프 생성 로직
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [역할]
    당신은 '문학 큐레이터'입니다. 책의 **'분위기', '정서', '철학'** 등 포괄적인 취향을 분석하여 책을 추천하십시오.
    
    [데이터 형식 조건]
    1. 총 15개 내외의 노드 생성.
    2. JSON 포맷 필수. 키 이름: "id", "author", "group", "summary", "reason".
    3. 구조: {{ "nodes": [ ... ], "edges": [ ... ] }} 형태를 반드시 유지할 것.
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
        st.error(f"서버 통신 오류 발생: {e}")
        return None

# 8. Pyvis 시각화 함수 (🌟 여기가 수정되었습니다!)
def visualize_network(data):
    net = Network(height="650px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 🌟 [긴급 패치] 데이터가 리스트(List)로 들어올 경우, 딕셔너리로 강제 변환
    if isinstance(data, list):
        # AI가 리스트만 줬다면, 그걸 'nodes'로 간주하고 'edges'는 빈 리스트로 처리
        data = {'nodes': data, 'edges': []}
    
    # 데이터가 딕셔너리가 아니거나 비어있으면 중단
    if not isinstance(data, dict):
        st.error("데이터 형식이 올바르지 않습니다. 다시 시도해주세요.")
        return None

    net.force_atlas_2based(
        gravity=-80,
        central_gravity=0.01,
        spring_length=200,
        spring_strength=0.05,
        damping=0.4
    )
    
    # .get()을 이제 안전하게 쓸 수 있음
    for node in data.get('nodes', []):
        if 'id' not in node:
            node['id'] = node.get('title', 'Unknown Book')

        group = node.get('group', 'Recommended')
        
        if group == 'Seed':
            color = "#FF6B6B"
            size = 40
        else:
            color = "#4ECDC4"
            size = 25
            
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
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target, color="rgba(200, 200, 255, 0.15)", width=1)
    
    return net

# 9. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 당신의 독서 취향을 우주에 연결하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            try:
                # 데이터 유효성 검사 추가
                if data:
                    net = visualize_network(data)
                    
                    if net:
                        path = "tmp_network.html"
                        net.save_graph(path)
                        
                        with open(path, 'r', encoding='utf-8') as f:
                            source_code = f.read()
                        
                        components.html(source_code, height=670)
                        st.success("분석 완료! 노드 위에 마우스를 올려보세요.")
                else:
                    st.error("AI가 유효한 데이터를 반환하지 못했습니다. 다시 시도해주세요.")
                
            except Exception as e:
                st.error(f"시각화 처리 중 오류가 발생했습니다: {e}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
