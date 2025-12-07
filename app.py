import streamlit as st
import networkx as nx
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components

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

# 5. HTML 카드 생성 함수 (줄바꿈 제거 패치 적용)
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
    
    # 🌟 [수정 핵심] f-string 내부의 줄바꿈을 없애야 브라우저가 HTML로 인식합니다.
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
    # 혹시 모를 줄바꿈 문자 제거 (가장 중요)
    return html.replace("\n", "")

# 6. 그래프 생성 로직
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [역할]
    당신은 독자의 내면과 영혼을 꿰뚫어 보는 '문학 큐레이터'입니다.
    책이 가진 고유의 **'분위기(Vibe)', '정서적 결', '철학적 깊이'** 등 포괄적인 취향을 분석하여 책을 추천하십시오.
    
    [데이터 형식 조건]
    1. 총 15개 내외의 노드 생성.
    2. JSON 포맷 필수 (키 이름 정확히): "id"(책제목), "author"(저자), "group"("Seed" or "Recommended"), "summary"(한줄요약), "reason"(추천이유).
    3. 추천 이유는 "A책의 우울함과 B책의 허무함이 연결됩니다"처럼 구체적이고 감성적으로 작성.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            text = result['candidates'][0]['content']['parts'][0]['text']
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        else:
            return None
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# 7. Pyvis 시각화 함수 (둥실둥실 물리 엔진 강화)
def visualize_network(data):
    # 배경색을 완전 검정보다는 아주 짙은 남색으로 설정하여 고급스럽게
    net = Network(height="650px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 🌟 둥실둥실 우주 유영 느낌의 물리 엔진 설정
    net.force_atlas_2based(
        gravity=-80,           # 서로 더 강하게 밀어내서 넓게 퍼짐
        central_gravity=0.01,  # 중앙으로 당기는 힘을 약하게
        spring_length=200,     # 연결선을 길게 늘어뜨림
        spring_strength=0.05,  # 스프링을 느슨하게 (출렁거림)
        damping=0.4            # 멈추는 속도를 늦춰서 계속 움직이는 느낌
    )
    
    for node in data.get('nodes', []):
        if 'id' not in node:
            node['id'] = node.get('title', 'Unknown Book')

        group = node.get('group', 'Recommended')
        
        if group == 'Seed':
            color = "#FF6B6B"
            size = 40          # 메인 책은 더 크게
        else:
            color = "#4ECDC4"
            size = 25
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_html, # 줄바꿈 제거된 HTML 입력
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=5,
            # 폰트 설정 추가
            font={'face': 'Noto Sans KR', 'size': 16, 'color': 'white', 'strokeWidth': 2, 'strokeColor': '#000000'} 
        )
    
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            # 선을 더 얇고 투명하게 해서 몽환적인 느낌
            net.add_edge(source, target, color="rgba(200, 200, 255, 0.15)", width=1)
    
    return net

# 8. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 당신의 독서 취향을 우주에 연결하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            try:
                net = visualize_network(data)
                
                path = "tmp_network.html"
                net.save_graph(path)
                
                with open(path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                components.html(source_code, height=670)
                st.success("분석 완료! 노드 위에 마우스를 올려보세요.")
                
            except Exception as e:
                st.error(f"시각화 처리 중 오류가 발생했습니다: {e}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
