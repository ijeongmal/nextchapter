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

# 6. JSON 추출 도우미 함수 (강화됨)
def extract_json(text):
    try:
        # 1차 시도: 순수 JSON 파싱
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    try:
        # 2차 시도: 텍스트 속에 숨어있는 JSON({ ... } 또는 [ ... ]) 찾기
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except Exception:
        pass
        
    return None

# 7. 그래프 생성 로직
def get_recommendations(books):
    # 🌟 안전성을 위해 모델을 1.5-flash로 잠시 변경 (가장 JSON을 잘 뱉음)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 책 3권: {books}
    
    [역할]
    당신은 '문학 큐레이터'입니다. 책의 분위기, 정서, 철학을 분석하여 추천하십시오.
    
    [필수 조건]
    1. 결과는 반드시 JSON 포맷이어야 합니다.
    2. 마크다운(```)을 쓰지 마십시오.
    3. 데이터 구조:
       {{
         "nodes": [
           {{"id": "책제목", "author": "저자", "group": "Seed" 또는 "Recommended", "summary": "한줄요약", "reason": "추천이유"}}
         ],
         "edges": [
           {{"source": "책제목A", "target": "책제목B"}}
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
            
            # 잡담 제거 시도
            cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
            data = extract_json(cleaned_text)
            
            if data is None:
                # 🌟 실패 시 원본 텍스트를 반환하여 에러 메시지로 띄움
                return {"error": "JSON 파싱 실패", "raw_text": raw_text}
            
            return data
        else:
            return {"error": "API 응답 없음", "raw_text": "Empty Response"}
            
    except Exception as e:
        return {"error": str(e), "raw_text": "Network Error"}

# 8. Pyvis 시각화 함수
def visualize_network(data):
    net = Network(height="650px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 🌟 리스트로 들어오면 딕셔너리로 변환 (list object has no attribute 'get' 방지)
    if isinstance(data, list):
        data = {'nodes': data, 'edges': []}
        
    # 데이터 검증
    if not isinstance(data, dict) or 'nodes' not in data:
        st.error("데이터 구조가 올바르지 않습니다.")
        return None

    net.force_atlas_2based(
        gravity=-80,
        central_gravity=0.01,
        spring_length=200,
        spring_strength=0.05,
        damping=0.4
    )
    
    for node in data.get('nodes', []):
        # id가 없으면 title을, 그것도 없으면 임의값 사용
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
        
        # 🌟 실패 원인 분석 및 표시 (여기가 중요합니다!)
        if data and "error" in data:
            st.error("AI가 데이터를 올바르게 생성하지 못했습니다. 다시 시도해주세요.")
            with st.expander("개발자용 디버그 정보 (에러 원인)"):
                st.write(f"Error Type: {data['error']}")
                st.code(data.get('raw_text', ''), language='json')
        
        elif data:
            try:
                net = visualize_network(data)
                
                if net:
                    path = "tmp_network.html"
                    net.save_graph(path)
                    with open(path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    components.html(source_code, height=670)
                    st.success("분석 완료! 노드 위에 마우스를 올려보세요.")
                else:
                    st.warning("그래프를 생성할 데이터가 충분하지 않습니다.")
                    
            except Exception as e:
                st.error(f"시각화 중 오류: {e}")
        else:
            st.error("알 수 없는 이유로 데이터가 비어있습니다.")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
