// ===== GPS 프론트엔드 =====
// 담당 기능:
//   1. 사건 생성: 근무지(지오펜스) 등록
//   2. 홈 화면: GPS 온오프 토글 → 핑 수집
//   3. 결과 화면: GPS 핑 시각화 (IN_WORKPLACE=파랑, OUTSIDE=주황, mocked=회색)

// ---------- 내부 상태 ----------
let _resultMap = null;   // 결과 지도 인스턴스

// ---------- 카카오맵 준비 확인 (결과 화면 시각화용) ----------
function _kakaoReady() {
  return typeof kakao !== 'undefined' && kakao.maps;
}

// ---------- 인증 헤더 (로그인 시 토큰 포함) ----------
// gps.js의 모든 API 호출은 이 헤더를 써야 한다.
// 토큰 누락 시 서버가 데모 유저로 처리 → 로그인 유저 소유 사건을 못 찾아 404.
function _gpsHeaders(json) {
  const h = {};
  if (json) h['Content-Type'] = 'application/json';
  try {
    const tk = (typeof getToken === 'function') ? getToken() : '';
    if (tk) h['Authorization'] = 'Bearer ' + tk;
  } catch (e) {}
  return h;
}

// ---------- GPS 체크박스 ON → 근무지·핑 정보 표시 ----------
document.getElementById('n_gchk').addEventListener('change', function (e) {
  const gbox = document.getElementById('gbox');
  gbox.style.display = e.target.checked ? 'block' : 'none';
  if (e.target.checked) {
    if (typeof refreshGpsInfo === 'function') refreshGpsInfo();
  }
});

// ---------- 사건 생성 화면: 근무지 위치 ----------
// 사건 정보 입력 시 f_wp(위도,경도)를 받아 사건 생성 직후 지오펜스로 등록한다.
// 한 번 등록하면 홈 토글 핑 판정·증거 분석에 모두 자동 사용된다.
function _registerCaseWorkplace() {
  const caseId = (typeof S !== 'undefined') && S.caseId;
  const el = document.getElementById('f_wp');
  if (!caseId || !el) return;
  const parts = (el.value || '').split(',').map(function (s) { return s.trim(); });
  const lat = parseFloat(parts[0]), lng = parseFloat(parts[1]);
  if (isNaN(lat) || isNaN(lng)) return;   // 미입력이면 등록 생략(선택 항목)
  const radiusEl = document.getElementById('f_wp_radius');
  const radius = radiusEl ? parseInt(radiusEl.value) || 100 : 100;

  fetch(window.apiUrl('/cases/' + caseId + '/gps/workplace'), {
    method: 'POST',
    headers: _gpsHeaders(true),
    body: JSON.stringify({ center_lat: lat, center_lng: lng, radius_m: radius }),
  })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function () {
      console.log('[GPS] 사건 근무지 등록:', lat, lng);
      if (typeof toast === 'function') toast('근무지가 등록됐어요. GPS 핑이 출퇴근으로 판정됩니다.');
    })
    .catch(function (e) {
      console.warn('[GPS] 근무지 등록 실패:', e);
      if (typeof toast === 'function') toast('근무지 등록 실패(' + e + '). 위치 형식을 확인하세요.');
    });
}

// ---------- 사건 생성 화면: 주소 검색 (카카오 Geocoder/Places) ----------
// 주소·건물명 → 좌표로 변환해 f_wp에 채운다. 카카오 services 라이브러리 필요.
function searchCaseAddress() {
  const q = (document.getElementById('f_wp_addr').value || '').trim();
  const box = document.getElementById('addrResults');
  if (!q) { alert('검색할 주소나 건물명을 입력하세요.'); return; }

  if (!_kakaoReady() || !kakao.maps.services) {
    if (box) {
      box.style.display = 'block';
      box.innerHTML =
        '<div style="padding:10px;font-size:12px;color:var(--muted)">'
        + '카카오맵을 불러올 수 없어요. <b>localhost:8000</b>으로 접속했는지 확인하세요'
        + '(127.0.0.1은 카카오에 등록된 도메인과 달라 차단됩니다). '
        + '또는 좌표를 직접 입력하세요.</div>';
    }
    return;
  }

  function _render(items) {
    if (!box) return;
    box.style.display = 'block';
    if (!items.length) { box.innerHTML = '<div style="padding:10px;font-size:12px;color:var(--muted)">검색 결과가 없어요.</div>'; return; }
    box.innerHTML = items.slice(0, 8).map(function (it) {
      const name = it.place_name || it.address_name || '';
      const addr = it.road_address_name || it.address_name || '';
      const lat = it.y, lng = it.x;
      return `<div onclick="pickCaseAddress(${lat},${lng},'${(name).replace(/'/g, '')}')" `
        + `style="padding:8px 10px;border-bottom:1px solid var(--line);cursor:pointer;font-size:13px">`
        + `<b>${name}</b><br><span class="small-muted">${addr}</span></div>`;
    }).join('');
  }

  const places = new kakao.maps.services.Places();
  places.keywordSearch(q, function (data, status) {
    if (status === kakao.maps.services.Status.OK && data.length) { _render(data); return; }
    // 키워드 결과 없으면 주소 검색으로 폴백
    const geocoder = new kakao.maps.services.Geocoder();
    geocoder.addressSearch(q, function (res, st2) {
      if (st2 === kakao.maps.services.Status.OK) _render(res);
      else _render([]);
    });
  });
}

// 검색 결과 클릭 → 좌표 채우고 결과창 닫기
function pickCaseAddress(lat, lng, name) {
  document.getElementById('f_wp').value = Number(lat).toFixed(7) + ',' + Number(lng).toFixed(7);
  if (name) {
    const wn = document.getElementById('f_wn');
    if (wn && !wn.value) wn.value = name;   // 사업장명이 비어있으면 채워줌
  }
  const box = document.getElementById('addrResults');
  if (box) box.style.display = 'none';
  if (typeof toast === 'function') toast('근무지 좌표가 입력됐어요.');
}

// 사건 생성 화면 "현재 위치" 버튼 → f_wp에 좌표 채움
function setCaseWorkplaceByGeo() {
  if (!navigator.geolocation) {
    alert('이 브라우저는 위치 서비스를 지원하지 않습니다.');
    return;
  }
  const btn = document.getElementById('btnCaseLoc');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader" style="animation:spin .8s linear infinite"></i>'; }
  navigator.geolocation.getCurrentPosition(
    function (pos) {
      document.getElementById('f_wp').value =
        pos.coords.latitude.toFixed(7) + ',' + pos.coords.longitude.toFixed(7);
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="ti ti-current-location"></i>'; }
    },
    function (err) {
      alert('위치 정보를 가져올 수 없습니다: ' + err.message);
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="ti ti-current-location"></i>'; }
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

// 업로드 화면 GPS 영역 진입 시: 등록된 근무지·수집된 핑 수를 자동 표시
function refreshGpsInfo() {
  const caseId = (typeof S !== 'undefined') && S.caseId;
  const txt = document.getElementById('gpsWpText');
  if (!caseId) {
    if (txt) txt.textContent = '먼저 사건을 만들어주세요.';
    return;
  }

  // 등록된 근무지 표시 (사건 생성 시 등록됨)
  fetch(window.apiUrl('/cases/' + caseId + '/gps/workplace'), { headers: _gpsHeaders(false) })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (w) {
      const hidden = document.getElementById('n_wp');
      if (w) {
        if (txt) txt.textContent =
          `등록된 근무지: ${Number(w.center_lat).toFixed(5)}, ${Number(w.center_lng).toFixed(5)} (반경 ${w.radius_m}m)`;
        if (hidden) hidden.value = `${w.center_lat},${w.center_lng},${w.radius_m}`;
      } else {
        if (txt) txt.textContent = '근무지가 등록되지 않았어요. 사건 정보 화면에서 위치를 입력하세요.';
      }
    })
    .catch(function () { if (txt) txt.textContent = '근무지 정보를 불러오지 못했어요.'; });

  // 수집된 핑 수 표시
  fetch(window.apiUrl('/cases/' + caseId + '/gps/logs'), { headers: _gpsHeaders(false) })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      const el = document.getElementById('gpsPingCount');
      if (el && d) el.textContent = `(현재 ${d.count}건 수집됨)`;
    })
    .catch(function () {});
}

// ---------- 결과 화면 GPS 핑 시각화 ----------
// analysis.js 또는 core.js에서 분석 결과 렌더 후 아래 함수를 호출합니다.
// 호출 방법: renderGpsMap(workplaceLat, workplaceLng, radiusM, pings)
//   pings: [{lat, lng, status, ts}] — status: "IN_WORKPLACE" | "OUTSIDE" | null(mocked)

function renderGpsMap(wpLat, wpLng, radiusM, pings) {
  const container = document.getElementById('result-map');
  if (!container) return;

  // 핑이 없으면 지도 숨김
  if (!pings || pings.length === 0) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';

  if (!_kakaoReady()) {
    container.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:12px">카카오맵 키를 설정해주세요</div>';
    return;
  }

  // 지도 초기화 (이미 있으면 재사용)
  const center = new kakao.maps.LatLng(wpLat, wpLng);
  if (!_resultMap) {
    _resultMap = new kakao.maps.Map(container, { center: center, level: 4 });
  } else {
    _resultMap.setCenter(center);
  }

  // 근무지 원(지오펜스) 표시
  new kakao.maps.Circle({
    map: _resultMap,
    center: center,
    radius: radiusM,
    strokeWeight: 2,
    strokeColor: '#2563eb',
    strokeOpacity: 0.8,
    fillColor: '#eef3fe',
    fillOpacity: 0.4,
  });

  // 근무지 중심 마커
  new kakao.maps.Marker({
    map: _resultMap,
    position: center,
    title: '근무지',
  });

  // GPS 핑 마커
  // IN_WORKPLACE → 파랑, OUTSIDE → 주황, mocked/null → 회색
  const COLOR = {
    IN_WORKPLACE: '#2563eb',
    OUTSIDE: '#f59e0b',
    null: '#9aa3b2',
    undefined: '#9aa3b2',
  };

  const bounds = new kakao.maps.LatLngBounds();
  bounds.extend(center);

  pings.forEach(function (p) {
    const pos = new kakao.maps.LatLng(p.lat, p.lng);
    bounds.extend(pos);

    const color = COLOR[p.status] || COLOR[undefined];
    const label = p.status === 'IN_WORKPLACE' ? '✓' : p.status === 'OUTSIDE' ? '✗' : '–';

    // 커스텀 오버레이로 색상 원 + 상태 표시
    const content = `<div style="
      width:22px;height:22px;border-radius:50%;
      background:${color};border:2px solid #fff;
      box-shadow:0 2px 6px rgba(0,0,0,.25);
      display:flex;align-items:center;justify-content:center;
      color:#fff;font-size:11px;font-weight:700;
      transform:translate(-11px,-11px);cursor:default;
      " title="${p.ts || ''}">${label}</div>`;

    new kakao.maps.CustomOverlay({
      map: _resultMap,
      position: pos,
      content: content,
      zIndex: 3,
    });
  });

  // 모든 핑이 보이도록 뷰 자동 조정
  _resultMap.setBounds(bounds, 40);
}

// 로딩 스피너 CSS (현재 위치 버튼용)
(function () {
  const s = document.createElement('style');
  s.textContent = '@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}';
  document.head.appendChild(s);
})();


// ===== GPS 온오프 토글 (홈 화면) =====
// - 기록 시작: 즉시 첫 핑 전송 → 이후 30초 간격 자동 전송 (운영은 5분)
// - 핑은 POST /cases/{id}/gps/ping → DB에 저장
// - 사용자는 버튼 하나만 누르면 됨. 좌표는 브라우저 GPS가 자동 수집.

let _gpsTracking = false;
let _gpsTimer = null;
let _gpsUiTimer = null;
let _lastPingTs = null;
let _todayPingCount = 0;

const GPS_PING_INTERVAL = 30 * 1000; // 30초 (데모), 운영은 5 * 60 * 1000

// 스위치 토글 핸들러 (체크박스 onchange)
function onGpsSwitch(checked) {
  // 사건(근무 등록)이 없으면 스위치를 되돌리고 등록 화면으로 유도
  if (!(typeof S !== 'undefined' && S.caseId)) {
    const input = document.getElementById('gpsSwitchInput');
    if (input) input.checked = false;
    if (typeof startNewCase === 'function') startNewCase();
    else if (typeof goUpload === 'function') goUpload();
    return;
  }
  checked ? _startTracking() : _stopTracking();
}

// 하위호환: 기존 호출부가 남아 있을 수 있어 유지
function toggleGpsTracking() {
  const input = document.getElementById('gpsSwitchInput');
  onGpsSwitch(input ? !input.checked : !_gpsTracking);
}

function _startTracking() {
  if (!navigator.geolocation) {
    alert('이 브라우저는 위치 서비스를 지원하지 않습니다.');
    const input = document.getElementById('gpsSwitchInput');
    if (input) input.checked = false;
    return;
  }
  _gpsTracking = true;
  _sendPing();                                          // 즉시 첫 핑 (근무지는 사건 생성 시 등록됨)
  _gpsTimer = setInterval(_sendPing, GPS_PING_INTERVAL);
  _gpsUiTimer = setInterval(_updateToggleCard, 5000);   // 카드 텍스트 주기 갱신
  _updateToggleCard();
}

function _stopTracking() {
  _gpsTracking = false;
  if (_gpsTimer)   { clearInterval(_gpsTimer);   _gpsTimer = null; }
  if (_gpsUiTimer) { clearInterval(_gpsUiTimer); _gpsUiTimer = null; }
  _updateToggleCard();
}

function _sendPing() {
  const caseId = (typeof S !== 'undefined') && S.caseId;
  if (!caseId) { _stopTracking(); return; }

  navigator.geolocation.getCurrentPosition(
    function (pos) {
      const body = {
        ts: new Date().toISOString(),
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        is_mocked: false,
        source: 'web_geo',
      };
      fetch(window.apiUrl('/cases/' + caseId + '/gps/ping'), {
        method: 'POST',
        headers: _gpsHeaders(true),
        body: JSON.stringify(body),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => {
          _lastPingTs = Date.now();
          _todayPingCount++;
          _updateToggleCard();
          console.log('[GPS ping]', data.status, data.distance_m + 'm',
            new Date().toLocaleTimeString('ko-KR'));
        })
        .catch(err => console.warn('[GPS] 핑 전송 실패:', err));
    },
    err => console.warn('[GPS] 위치 조회 실패:', err.message),
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

// ---------- 토글 카드 UI 갱신 ----------
function _updateToggleCard() {
  const card    = document.getElementById('gpsToggleCard');
  const title   = document.getElementById('gpsToggleTitle');
  const sub     = document.getElementById('gpsToggleSub');
  const input   = document.getElementById('gpsSwitchInput');
  if (!card || !input) return;

  const hasCaseId = !!((typeof S !== 'undefined') && S.caseId);

  // 사건이 없으면: 스위치 OFF + 안내 문구 (클릭 시 등록 화면으로 유도)
  if (!hasCaseId) {
    card.classList.remove('on');
    input.checked = false;
    title.textContent = '근무지 GPS 기록';
    sub.textContent   = '근무를 시작했다면 미리 기록을 켜두세요 (분쟁 전부터 출근 증거 축적)';
    return;
  }

  // 사건이 있으면 스위치 상태 = 추적 여부와 동기화
  input.checked = _gpsTracking;

  if (_gpsTracking) {
    card.classList.add('on');
    title.innerHTML = '<span class="gps-ping-dot"></span>GPS 기록 중';
    const ageSec = _lastPingTs
      ? Math.round((Date.now() - _lastPingTs) / 1000)
      : null;
    sub.textContent = _todayPingCount > 0
      ? `오늘 ${_todayPingCount}회 기록 · ${ageSec}초 전 핑`
      : '첫 핑 전송 중...';
  } else {
    card.classList.remove('on');
    title.textContent = '근무지 GPS 기록';
    sub.textContent   = _todayPingCount > 0
      ? `오늘 ${_todayPingCount}회 기록됨 · 꺼짐`
      : '스위치를 켜서 출근 기록을 시작하세요';
  }
}

// 홈 화면 진입할 때마다 카드 갱신 (goPage 훅 + MutationObserver 폴백)
(function () {
  // 스위치 + 슬라이더 CSS 주입 (styles.css는 UI 담당 영역이라 건드리지 않음)
  const css = document.createElement('style');
  css.textContent = `
    .gps-switch{position:relative;display:inline-block;width:46px;height:26px;flex:none;cursor:pointer}
    .gps-switch input{opacity:0;width:0;height:0;position:absolute}
    .gps-switch-slider{position:absolute;inset:0;background:#cbd2dc;border-radius:999px;transition:background .2s}
    .gps-switch-slider::before{content:"";position:absolute;width:20px;height:20px;left:3px;top:3px;background:#fff;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.3);transition:transform .2s}
    .gps-switch input:checked + .gps-switch-slider{background:#2563eb}
    .gps-switch input:checked + .gps-switch-slider::before{transform:translateX(20px)}
    #f_wp_radius{-webkit-appearance:none;appearance:none;height:6px;border-radius:3px;background:#e2e8f0;outline:none;padding:0}
    #f_wp_radius::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;border-radius:50%;background:#2563eb;cursor:pointer;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3)}
    #f_wp_radius::-moz-range-thumb{width:20px;height:20px;border-radius:50%;background:#2563eb;cursor:pointer;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3)}
  `;
  document.head.appendChild(css);

  // 방법 1: goPage 래핑 (core.js가 먼저 로드됐을 때)
  function _wrapGoPage() {
    const _orig = window.goPage;
    if (typeof _orig === 'function' && !_orig._gpsWrapped) {
      window.goPage = function (id, nav) {
        _orig(id, nav);
        if (id === 'home') setTimeout(_updateToggleCard, 50);
      };
      window.goPage._gpsWrapped = true;
    }
  }

  // 방법 1-b: submitCase 래핑 → 사건 생성 직후 카드 즉시 갱신 + 근무지 등록
  function _wrapSubmitCase() {
    // case.js의 submitCase는 전역 function 선언이지만
    // window 속성으로 접근이 안 될 수 있어(let S와 같은 이유).
    // 안전하게: submit 버튼 클릭을 감지해서 사건 생성 후 근무지 등록.
    const origFn = (typeof submitCase === 'function') ? submitCase : null;
    if (!origFn || origFn._gpsWrapped) return;

    window.submitCase = async function () {
      const r = await origFn.apply(this, arguments);
      setTimeout(_updateToggleCard, 50);
      _registerCaseWorkplace();
      return r;
    };
    window.submitCase._gpsWrapped = true;
    // 전역 이름도 덮어쓰기 (onclick="submitCase()" 호출 대비)
  }

  // 방법 2: home 페이지가 active 될 때 감지 (래핑 실패 폴백)
  function _observeHome() {
    const home = document.getElementById('home');
    if (!home) return;
    const obs = new MutationObserver(function () {
      if (home.classList.contains('active')) _updateToggleCard();
    });
    obs.observe(home, { attributes: true, attributeFilter: ['class'] });
  }

  function _init() {
    _wrapGoPage();
    _wrapSubmitCase();
    _observeHome();
    setTimeout(_updateToggleCard, 150);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }
})();
