import streamlit as st
import networkx as nx
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components

# 1. 페이지 설정 및 폰트 로드
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 한글 폰트(Noto Sans KR) 웹 로딩 (깨짐 방지)
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
st.markdown("세 권의 책을 입력하면, 단순 분류를 넘어 **당신의 포괄적인 문학적 취향(분위기, 정서, 철학)**을 분석하여 도서 우주를 연결해 드립니다.")

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

# 5. HTML 카드 생성 함수 (다크 모드 디자인)
def create_tooltip_html(node_data):
    bg_color = "#1E222B"
    text_color = "#FFFFFF"
    
    # 그룹 확인 (기본값 Recommended)
    group = node_data.get('group', 'Recommended')
    accent_color = "#4ECDC4" if group == 'Recommended' else "#FF6B6B"
    badge_text = "RECOMMENDED" if group == 'Recommended' else "SEED BOOK"
    
    # 🌟 데이터 안전 장치 (id나 title 중 있는 것을 사용)
    book_title = node_data.get('id') or node_data.get('title') or "제목 없음"
    author = node_data.get('author', '저자 미상')
    reason = node_data.get('reason', '상세 분석 내용이 없습니다.')
    summary = node_data.get('summary', '줄거리 정보가 없습니다.')
    
    html = f"""
    <div style="
        font-family: 'Noto Sans KR', sans-serif;
        background-color: {bg_color};
        color: {text_color};
        padding: 20px;
        border-radius: 12px;
        width: 320px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border: 1px solid #333;
        text-align: left;
    ">
        <div style="
            display: inline-block;
            background-color: {accent_color};
            color: #1e1e1e;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            margin-bottom: 10px;
        ">
            {badge_text}
        </div>
        <h3 style="margin: 0 0 5px 0; font-size: 20px; font-weight: 700;">{book_title}</h3>
        <p style="margin: 0 0 15px 0; font-size: 13px; color: #aaaaaa;">👤 {author}</p>
        
        <div style="
            background-color: #2C303A;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid {accent_color};
        ">
            <p style="margin: 0 0 5px 0; font-size: 11px; color: #888; font-weight: bold;">💡 추천 이유 (취향 분석)</p>
            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #eee;">
                {reason}
            </p>
        </div>
        
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #777; border-top: 1px solid #444; padding-top: 8px;">
            📖 {summary}
        </p>
    </div>
    """
    return html

# 6. 그래프 생성 로직 (프롬프트 대폭 강화)
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # 🌟 [핵심] 포괄적 취향 분석을 위한 강력한 프롬프트
    prompt = f"""
    사용자가 입력한 인생 책 3권: {books}
    
    [당신의 역할]
    당신은 단순한 사서가 아니라, 독자의 내면과 영혼을 꿰뚫어 보는 '문학 큐레이터'입니다.
    단순히 장르나 소재가 비슷한 책을 찾지 마십시오.
    책이 가진 고유의 **'분위기(Vibe)', '정서적 결(Texture)', '철학적 깊이', '문체의 미학'** 등 **포괄적인 취향(Comprehensive Taste)**을 분석하여 책을 추천해야 합니다.
    
    [추천 기준]
    1. 사용자가 입력한 책들 사이의 보이지 않는 공통점(예: "도시의 쓸쓸함", "치열한 지적 탐구", "따뜻한 휴머니즘")을 찾아내십시오.
    2. 추천하는 책은 그 '공통된 취향'의 연장선에 있어야 합니다.
    3. 추천 이유는 "이 책도 추리소설이라서" 같은 단순한 이유가 아니라, **"당신이 데미안에서 느꼈던 자아 탐구의 치열함을 이 책의 주인공에게서도 발견할 수 있기 때문입니다"**와 같이 구체적이고 감성적으로 작성하십시오.
    
    [출력 데이터 형식 (JSON 필수)]
    총 15개 내외의 노드를 구성하여 아래 JSON 포맷으로만 출력하십시오 (마크다운 없이):
    {{
        "nodes": [
            {{
                "id": "책 제목 (정확히 기입)",
                "author": "저자 이름",
                "group": "Seed" (입력한 책) 또는 "Recommended" (추천 책),
                "summary": "책의 핵심 줄거리 한 줄 요약",
                "reason": "위의 [추천 기준]에 맞춘 깊이 있는 추천 사유"
            }},
            ...
        ],
        "edges": [
            {{"source": "책 제목 A", "target": "책 제목 B"}},
            ...
        ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            text = result['candidates'][0]['content']['parts'][0]['text']
            # JSON 정제
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        else:
            return None
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# 7. Pyvis 시각화 함수 (물리 엔진 적용)
def visualize_network(data):
    net = Network(height="650px", width="100%", bgcolor="#0e1117", font_color="white")
    
    # 🌟 둥실둥실한 우주 느낌의 물리 엔진 설정
    net.force_atlas_2based(
        gravity=-60,           # 서로 적당히 밀어냄
        central_gravity=0.015, # 가운데로 은은하게 당김
        spring_length=180,     # 연결선을 조금 길게
        spring_strength=0.08,  # 탄성
        damping=0.4            # 부드러운 움직임
    )
    
    # 노드 추가
    for node in data.get('nodes', []):
        # 🌟 안전장치: id가 없으면 title을 id로 사용 (KeyError 방지)
        if 'id' not in node:
            node['id'] = node.get('title', 'Unknown Book')

        group = node.get('group', 'Recommended')
        
        if group == 'Seed':
            color = "#FF6B6B" # 강조색 (코랄)
            size = 35         # 입력한 책은 더 크게
        else:
            color = "#4ECDC4" # 추천색 (민트)
            size = 20
            
        tooltip_html = create_tooltip_html(node)
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_html, # HTML 툴팁 연결
            color=color, 
            size=size,
            borderWidth=2,
            borderWidthSelected=4
        )
    
    # 엣지 추가
    for edge in data.get('edges', []):
        source = edge.get('source')
        target = edge.get('target')
        if source and target:
            net.add_edge(source, target, color="rgba(255, 255, 255, 0.2)")
    
    return net

# 8. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 당신의 독서 취향을 깊이 있게 분석하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            try:
                net = visualize_network(data)
                
                # HTML 저장 및 표시
                path = "tmp_network.html"
                net.save_graph(path)
                
                with open(path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                components.html(source_code, height=670)
                st.success("분석 완료! 노드 위에 마우스를 올려 추천 이유를 확인하세요.")
                
            except Exception as e:
                st.error(f"시각화 처리 중 오류가 발생했습니다: {e}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
