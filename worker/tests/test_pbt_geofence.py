"""PBT — geofence 규칙 엔진 속성 테스트.

속성:
- invariant: 태깅된 로그 수 = 입력 로그 수
- invariant: excluded가 아닌 로그는 status가 IN_WORKPLACE 또는 OUTSIDE
- invariant: is_delayed_upload=True인 로그는 excluded=True
- invariant: is_mocked=True인 로그는 excluded=True
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from rules.geofence import tag_logs

gps_log = st.fixed_dictionaries({
    "ts": st.datetimes(),
    "lat": st.floats(min_value=33.0, max_value=39.0, allow_nan=False),
    "lng": st.floats(min_value=124.0, max_value=132.0, allow_nan=False),
    "is_mocked": st.booleans(),
    "is_delayed_upload": st.booleans(),
})
gps_logs = st.lists(gps_log, max_size=50)

center_lat = st.floats(min_value=33.0, max_value=39.0, allow_nan=False)
center_lng = st.floats(min_value=124.0, max_value=132.0, allow_nan=False)
radius = st.integers(min_value=10, max_value=500)


@given(logs=gps_logs, lat=center_lat, lng=center_lng, r=radius)
@settings(max_examples=100)
def test_invariant_count_preserved(logs, lat, lng, r):
    """태깅된 로그 수 = 입력 로그 수."""
    tagged = tag_logs(logs, lat, lng, r)
    assert len(tagged) == len(logs)


@given(logs=gps_logs, lat=center_lat, lng=center_lng, r=radius)
@settings(max_examples=100)
def test_invariant_non_excluded_have_status(logs, lat, lng, r):
    """excluded가 아닌 로그는 IN_WORKPLACE 또는 OUTSIDE."""
    tagged = tag_logs(logs, lat, lng, r)
    for t in tagged:
        if not t.get("excluded"):
            assert t.get("status") in ("IN_WORKPLACE", "OUTSIDE")


@given(logs=gps_logs, lat=center_lat, lng=center_lng, r=radius)
@settings(max_examples=100)
def test_invariant_delayed_excluded(logs, lat, lng, r):
    """is_delayed_upload=True 로그는 excluded=True."""
    tagged = tag_logs(logs, lat, lng, r)
    for i, t in enumerate(tagged):
        if logs[i].get("is_delayed_upload"):
            assert t.get("excluded") is True


@given(logs=gps_logs, lat=center_lat, lng=center_lng, r=radius)
@settings(max_examples=100)
def test_invariant_mocked_excluded(logs, lat, lng, r):
    """is_mocked=True 로그는 excluded=True."""
    tagged = tag_logs(logs, lat, lng, r)
    for i, t in enumerate(tagged):
        if logs[i].get("is_mocked"):
            assert t.get("excluded") is True
