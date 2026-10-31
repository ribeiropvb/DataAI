from dataai.tools.inspect import find_narrative
from dataai.tools.refs import ALLOWED_CONSTANTS, RefError, render_markers, unresolved_numbers


def test_narrative_detection():
    assert find_narrative("O aumento demonstra falha da estratégia")
    assert find_narrative("Engenharia lidera a evasão")
    assert not find_narrative("Ocorrências por mês")
    assert not find_narrative("Taxa de evasão no 1º ano por curso")


def test_markers_and_raw_numbers():
    res = {"result_id": "r", "values": {"x": 0.1234}, "rows": [{"g": "A", "v": 3}]}
    refs = []
    out = render_markers("Taxa {{r:x|percent_1}}; A = {{r:rows[g=A].v|integer}}; {{const:80%}}", lambda _: res, refs)
    assert out == "Taxa 12,3%; A = 3; 80%"
    assert len(refs) == 3
    assert unresolved_numbers("caiu 36% em 2024") == ["36%"]
    try:
        render_markers("{{const:42%}}", lambda _: res)
        raise AssertionError("constante não documentada deveria falhar")
    except RefError:
        pass
    assert "80%" in ALLOWED_CONSTANTS
