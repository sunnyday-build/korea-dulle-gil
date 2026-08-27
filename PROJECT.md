# 코리아둘레길 걷기 — 프로젝트 이어가기 문서

> 작성일 2026-08-27. 이 문서만 보면 어디서든 바로 이어서 작업할 수 있게 정리한 핸드오프 노트.

## 한 줄 요약
두루누비를 참고한 **모바일용 코리아둘레길 걷기 기록 웹앱**(단일 HTML). 지도에서 걸은 코스를 표시하고 진행률을 관리한다. 지금 **지도 엔진을 카카오맵으로 교체**했고, **GitHub Pages 배포 + 카카오 도메인 등록**만 하면 완성 단계.

---

## 파일 위치
- **앱 본체**: `/Users/sunyoung/korea-dulle-gil/index.html` (단일 파일, ~690KB, 경로 좌표가 안에 임베드됨)
- **빌드 자료**(재생성·재패치용): `/Users/sunyoung/korea-dulle-gil/build/`
  - `fetch_gpx3.py` — 두루누비에서 GPX 받아 가공 → `real_routes.json` 생성
  - `real_routes.json` — 가공된 297개 코스 좌표 (index.html에 이미 반영됨)
  - `patch3.py`, `patch4.py` — index.html에 데이터/카카오맵 반영했던 패치 스크립트(참고용 기록)
- **로컬 실행**: 해당 폴더에서 `python3 -m http.server 8777` → `http://localhost:8777/index.html`

---

## 현재 앱 기능 (구현 완료)
탭 3개: **지도·기록 / 코스 / 기록**

- **지도**: 카카오맵 위에 코리아둘레길 **297개 공식 코스**를 구간색으로 표시
  - 구간색: 해파랑길(파랑 `#2f7fd1`), 남파랑길(주황 `#e2953a`), 서해랑길(빨강 `#d1552f`), DMZ 평화의 길(초록 `#3aa06a`)
  - **안 걸은 코스**: 연하게(opacity .55) / **걸은(체크) 코스**: 진하게(굵게)
- **걸은 코스 기록 버튼**: 누르면 선택 모드 → 지도에서 코스 선을 **탭하면 색칠**(완주 표시). 카카오 폴리라인은 클릭 이벤트가 없어 **mousedown**으로 탭 처리.
- **구간 드롭다운**(상단): 전체 / 4구간 — 선택한 길만 지도에 표시, 화면 자동 이동
- **걸은 코스 검색**(상단 검색창): 걸은 코스만 검색 → 선택 시 그 코스로 확대 + 이름·거리 팝업
- **코스 경계 점 + 코스 번호**: 확대하면(경계점 level ≤ 9, 번호 level ≤ 6) 코스 구분이 보임
- **내 위치 버튼**(우하단, 걷기 시작 버튼 위): Figma 십자선 아이콘, 카카오 CustomOverlay 초록 점
- **코스 탭**: 구간별 코스 그리드 체크(지도와 양방향 연동) + 전체 진행률(%)/거리
- **기록 탭**: (구) GPS 산책 로그 — 현재 GPS 실시간 기록은 미사용이라 **비어있음/사실상 죽은 탭** → 제거 후보

### 설계 결정 메모
- GPS 실시간 기록(걷기 시작→경로 추적) 모델을 **수동 코스 체크 모델**로 전환함(사용자 요청). 관련 GPS 함수는 코드에 남아있으나 호출되지 않음(dead code).
- 진행률·거리·코스수는 전부 **실제 데이터(297코스/약 4,638km)** 기준.

---

## 데이터 파이프라인 (중요)
**출처**: 두루누비 웹사이트 내부 API (공공데이터포털 API는 142코스만 있어 구멍이 많아 사용 안 함)

- 코스 목록: `GET https://www.durunubi.kr/api/course/list?type=DNWW&serviceFlag={FLAG}&offset=0&size=2000&orderBy=4`
  - FLAG: `HE`(해파랑 50) / `NA`(남파랑 90) / `SEO`(서해랑 109) / `DMZ`(DMZ 48) = **297코스**
  - 응답 각 코스에 `gpx_src`(상대경로), `crs_Kor_Nm`, `crs_Dstnc` 등
- GPX 파일: `https://www.durunubi.kr/editImgUp.do?filePath={gpx_src}`
- 가공(`fetch_gpx3.py`):
  - 원본 GPX의 `<trkpt lat lon>` 파싱
  - **큰 점프(>700m) 지점에서 선을 끊음** → 바다/육지 가로지르는 가짜 직선 제거(페리·다리·데이터 끊김). 진짜 방조제(원본이 50m 간격 촘촘)는 유지됨.
  - 각 조각을 RDP 단순화(eps 0.00015 ≈ 16m)
- 결과 구조(`real_routes.json`), 코스 1개 =
  ```json
  {"id":0,"no":1,"name":"해파랑길 1코스","km":16.9,
   "segs":[[[lat,lon],...],[...]], "start":[lat,lon],"mid":[lat,lon],"end":[lat,lon]}
  ```
  - `segs`: 조각(점프로 끊긴) 배열 → 카카오 Polyline 여러 개로 그림
  - `start/end`: 경계 점, `mid`: 번호 라벨 위치
- **재생성 방법**: `cd build && python3 fetch_gpx3.py` → `real_routes.json` 갱신 → index.html의 `const REAL_ROUTES = ...` 부분 교체

---

## 카카오맵 연동
- **JavaScript 키**: `2c014f51c0251eb88b3c1ecb9cd9f18d` (카카오 앱: "코리아둘레길 걷기", ID 1558643)
- SDK 로드: `<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey=...&autoload=false"></script>` + `kakao.maps.load(initMap)`
- 카카오 레벨: 작을수록 확대. 초기 level 13(전국), 번호 라벨 level ≤ 6, 경계점 ≤ 9.

### ⚠️ 현재 막힌 지점 (해결 필요)
카카오 키는 **등록된 도메인에서만** 작동. 확인된 에러:
```
domain mismatched! caller=http://localhost:8777. check out registered web domains.
```
- `http://localhost:8777` 을 카카오 Web 플랫폼에 등록하려 했으나 콘솔이 **"유효하지 않은 링크"**로 거부(포트/ localhost 이슈로 추정).
- **결론**: localhost 대신 **실도메인(GitHub Pages)에 배포하고 그 도메인을 등록**하는 게 정답. HTTPS라 폰에서 **내 위치 기능도 작동**.

---

## 다음 할 일 (여기서 이어가기)

### 1) GitHub Pages 배포
이 컴퓨터엔 `gh`·git 인증·SSH키가 없음. 두 경로 중 택1:

**A. 웹 업로드(지금 당장, 개발설정 불필요)**
1. github.com/new → 공개 저장소 생성 (예: `korea-dulle-gil`)
2. 저장소 → **Add file → Upload files** → `index.html` 드래그 → Commit
3. **Settings → Pages** → Source: `Deploy from a branch`, Branch: `main` `/(root)` → Save
4. 1분 뒤 주소 확인: `https://<아이디>.github.io/korea-dulle-gil/`

**B. GitHub MCP로 자동화(다음 세션부터 가능)**
```
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
```
→ **Claude Code 새 세션 시작** → `/mcp` → github → Authenticate(브라우저)
→ 그 세션에서 "배포해줘" 하면 저장소 생성·업로드·Pages까지 대행 가능.
(※ 이번 세션엔 GitHub MCP 미연결 상태 확인됨.)

### 2) 카카오 도메인 등록
배포 주소가 나오면 카카오 개발자 콘솔 → 앱 → **플랫폼(Web)** → 사이트 도메인에 **호스트만** 등록:
```
https://<아이디>.github.io
```
(경로·슬래시 없이 호스트만. 카카오는 호스트 기준으로 매칭)

### 3) 확인
- 배포 주소 접속 → 지도 정상 표시 확인
- 폰에서 같은 주소 열기 → **내 위치** 버튼까지 동작(HTTPS)

---

## 남은 개선 후보 (선택)
- **기록 탭 제거** — GPS 미사용이라 빈 탭. 지도·코스 2탭으로 단순화 추천.
- 방조제 등 실제 장거리 직선(최대 ~6km)은 실제 트레일이라 유지 중 — 필요 시 별도 처리.
- 코스 번호가 확대해야만 보임 — 항상 표시/토글 옵션 검토 가능.

---

## 참고: 되돌리기
- 카카오 전환 직전 백업: `/Users/sunyoung/korea-dulle-gil/index.html.bak`
