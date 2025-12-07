import streamlit as st
import networkx as nx
from pyvis.network import Network
import requests
import json
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="Literary Nexus", layout="wide")

# 2. 제목 및 설명
st.title("📚 AI 기반 도서 추천 네트워크")
st.markdown("""
<style>
.big-font { font-size:18px !important; }
</style>
<p class="big-font">
세 권의 책을 입력하면, 단순한 장르를 넘어 <b>문체, 철학, 난이도</b> 등 포괄적인 취향을 분석하여 책을 연결해 드립니다.<br>
생성된 네트워크의 <b>노드(점)에 마우스를 올리면 추천 이유</b>를 볼 수 있습니다.
</p>
""", unsafe_allow_html=True)

# 3. API 키 가져오기
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ API 키 설정을 확인해주세요. (Manage app -> Secrets)")
    st.stop()

# 4. 사이드바 입력창
with st.sidebar:
    st.header("나의 인생 책 3권")
    book1 = st.text_input("첫 번째 책", placeholder="예: 데미안")
    book2 = st.text_input("두 번째 책", placeholder="예: 총, 균, 쇠")
    book3 = st.text_input("세 번째 책", placeholder="예: 1984")
    analyze_btn = st.button("네트워크 생성하기")

# 5. 그래프 생성 로직 (Gemini 2.5 Flash)
def get_recommendations(books):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # 🌟 프롬프트 대폭 강화: 추천 이유와 줄거리까지 요청
    prompt = f"""
    사용자가 입력한 3권의 책: {books}
    
    [목표]
    이 책들을 기반으로 '포괄적인 취향(문체, 철학, 난이도, 분위기)'이 유사한 도서 추천 네트워크를 구성해줘.
    단순한 장르 추천이 아니라, "이 작가의 건조한 문체를 좋아한다면 이 책도 좋아할 것" 같은 깊이 있는 연결이 필요해.
    
    [출력 조건]
    1. 입력된 책(Seed)과 추천된 책(Recommended)을 포함하여 총 15~20권 내외의 노드를 구성해.
    2. 각 책마다 다음 정보를 포함해:
       - title: 책 제목
       - summary: 책의 핵심 줄거리나 내용 (1~2문장)
       - reason: 이 책이 추천된 구체적인 이유 (입력된 책과의 공통점, 문체적 특성 등)
       - group: "Seed"(입력한 책) 또는 "Recommended"(추천된 책)
    3. 책들 간의 연관성이 있다면 엣지(선)로 연결해.
    4. 결과는 오직 JSON 형식으로만 출력해.
    
    [JSON 형식 예시]
    {{
        "nodes": [
            {{"id": "데미안", "group": "Seed", "summary": "자아를 찾아가는...", "reason": "입력하신 책입니다."}},
            {{"id": "이방인", "group": "Recommended", "summary": "어머니의 죽음 이후...", "reason": "데미안의 내면 탐구와 유사한 실존주의적 철학을 담고 있어 추천합니다."}}
        ],
        "edges": [
            {{"source": "데미안", "target": "이방인"}}
        ]
    }}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
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

# 6. Pyvis 시각화 함수
def visualize_network(data):
    # 네트워크 객체 생성 (높이, 너비, 배경색 등 설정)
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # 물리 엔진 설정 (노드들이 쫀득하게 움직이도록)
    net.force_atlas_2based()
    
    # 노드 추가
    for node in data.get('nodes', []):
        # 그룹별 색상 및 크기 설정
        if node['group'] == 'Seed':
            color = "#ff6b6b" # 빨간색 (입력한 책)
            size = 25
        else:
            color = "#4ecdc4" # 민트색 (추천된 책)
            size = 15
            
        # 🌟 핵심: title 속성에 HTML을 넣으면 마우스 오버 시 예쁜 툴팁이 뜹니다.
        tooltip_content = f"""
        <div style="font-family: sans-serif; padding: 10px; max-width: 300px;">
            <h4 style="margin: 0 0 10px 0;">📖 {node['id']}</h4>
            <p><b>💡 추천 이유:</b><br>{node.get('reason', '')}</p>
            <hr style="margin: 5px 0;">
            <p style="font-size: 0.9em; color: #555;"><b>줄거리:</b><br>{node.get('summary', '')}</p>
        </div>
        """
        
        net.add_node(
            node['id'], 
            label=node['id'], 
            title=tooltip_content, # 여기가 툴팁 내용
            color=color, 
            size=size,
            borderWidth=2
        )
    
    # 엣지 추가
    for edge in data.get('edges', []):
        net.add_edge(edge['source'], edge['target'], color="#cccccc")
    
    # 설정 옵션 (필요시 주석 해제하여 물리 엔진 조절 가능)
    # net.show_buttons(filter_=['physics'])
    
    return net

# 7. 메인 실행
if analyze_btn and book1 and book2 and book3:
    with st.spinner("AI가 책들의 영혼을 연결하고 있습니다..."):
        data = get_recommendations([book1, book2, book3])
        
        if data:
            # 네트워크 생성
            net = visualize_network(data)
            
            # HTML 파일로 저장 후 Streamlit에 표시
            try:
                # 임시 파일로 저장
                path = "tmp_network.html"
                net.save_graph(path)
                
                # HTML 파일 읽어서 렌더링
                with open(path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                components.html(source_code, height=620)
                
                st.success("네트워크가 생성되었습니다! 노드 위에 마우스를 올려보세요.")
                
            except Exception as e:
                st.error(f"시각화 중 오류가 발생했습니다: {e}")

elif analyze_btn:
    st.warning("책 3권을 모두 입력해주세요.")
