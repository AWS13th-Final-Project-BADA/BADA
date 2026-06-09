// ===== GPS 프론트엔드 — 카카오맵 연동 =====
// 담당 기능:
//   1. 업로드 화면: 근무지 등록 지도 (클릭 → 좌표 자동 입력)
//   2. 업로드 화면: 현재 위치 버튼 → 브라우저 Geolocation
//   3. 결과 화면: GPS 핑 시각화 (IN_WORKPLACE=파랑, OUTSIDE=주황, mocked=회색)

// ---------- 내부 상태 ----------
let _wpMap = null;       // 근무지 등록 지도 인스턴스
let _wpMarker = null;    // 근무지 마커
let _resultMap = null;   // 결과 지도 인스턴스

// ---------- 카카오맵 준비 확인 ----------
function _kakaoReady() {
  return typeof kakao !== 'undefined' && kakao.maps;
}

// ---------- 1. GPS 체크박스 ON → 근무지 등록 지도 초기화 ----------
document.getElementById('n_gchk').addEventListener('change', function (e) {
  const gbox = document.getElementById('gbox');
  gbox.style.display = e.target.checked ? 'block' : 'none';
  if (e.target.checked) {
    // 약간 지연 후 지도 초기화 (DOM 렌더 완료 대기)
    setTimeout(initWorkplaceMap, 100);
  }
});

function initWorkplaceMap() {
  if (!_kakaoReady()) {
    document.getElementById('wp-map').innerHTML =
      '<span style="color:var(--muted);font-size:12px">카카오맵 키를 설정해주세요 (index.html &lt;head&gt;)</span>';
    return;
  }
  if (_wpMap) return; // 이미 초기화됨

  const container = document.getElementById('wp-map');
  container.innerHTML = ''; // placeholder 텍스트 제거

  // 기존 입력값이 있으면 그 좌표로 중심 설정, 없으면 서울 시청
  const existing = _parseWpInput();
  const center = existing
    ? new kakao.maps.LatLng(existing.lat, existing.lng)
    : new kakao.maps.LatLng(37.5665, 126.9780);

  _wpMap = new kakao.maps.Map(container, {
    center: center,
    level: 4,
  });

  // 기존 좌표가 있으면 마커도 표시
  if (existing) {
    _setWpMarker(new kakao.maps.LatLng(existing.lat, existing.lng));
  }

  // 지도 클릭 → 근무지 마커 + 좌표 입력
  kakao.maps.event.addListener(_wpMap, 'click', function (mouseEvent) {
    const latlng = mouseEvent.latLng;
    _setWpMarker(latlng);
    _fillWpInput(latlng.getLat(), latlng.getLng());
  });
}

function _setWpMarker(latlng) {
  if (_wpMarker) _wpMarker.setMap(null);
  _wpMarker = new kakao.maps.Marker({ position: latlng, map: _wpMap });
  _wpMap.setCenter(latlng);
}

function _fillWpInput(lat, lng) {
  const existing = _parseWpInput();
  const radius = existing ? existing.radius : 50;
  document.getElementById('n_wp').value =
    `${lat.toFixed(7)},${lng.toFixed(7)},${radius}`;
}

function _parseWpInput() {
  const v = (document.getElementById('n_wp').value || '').split(',').map(s => s.trim());
  if (v.length >= 2 && !isNaN(parseFloat(v[0]))) {
    return {
      lat: parseFloat(v[0]),
      lng: parseFloat(v[1]),
      radius: parseInt(v[2]) || 50,
    };
  }
  return null;
}

// ---------- 2. 현재 위치 버튼 ----------
function setWorkplaceByGeo() {
  if (!navigator.geolocation) {
    alert('이 브라우저는 위치 서비스를 지원하지 않습니다.');
    return;
  }
  const btn = document.getElementById('btnMyLoc');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader" style="animation:spin .8s linear infinite"></i>';

  navigator.geolocation.getCurrentPosition(
    function (pos) {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      _fillWpInput(lat, lng);
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-current-location"></i>';

      // 지도가 열려있으면 해당 위치로 이동
      if (_kakaoReady() && _wpMap) {
        const latlng = new kakao.maps.LatLng(lat, lng);
        _setWpMarker(latlng);
      }
    },
    function (err) {
      alert('위치 정보를 가져올 수 없습니다: ' + err.message);
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-current-location"></i>';
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

// ---------- 3. 결과 화면 GPS 핑 시각화 ----------
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
