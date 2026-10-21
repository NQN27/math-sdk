"""Book events for Boss Lines v3.

Every event carries `index` and `type`. Board rows are emitted padded
(row + 1) when config.include_padding is on, the same convention as the SDK's
own events, so the frontend can index its padded board directly.
"""
from src.events.events import reveal_event


def _row(gs, r):
    return r + 1 if gs.config.include_padding else r


def pos(gs, c, r):
    return {"reel": c, "row": _row(gs, r)}


def _value(sym):
    """Weapon damage factor shown on the board (Bomb/Sword/Lightning); 0 otherwise."""
    return getattr(sym, "prize", 0) or 0


def emit(gs, etype, **data):
    gs.book.add_event({"index": len(gs.book.events), "type": etype, **data})


def boss_state_event(gs):
    emit(gs, "bossState", stage=gs.stage_label(), bosses=[
        {"id": b["id"], "reels": list(b["zone"]), "hp": b["hp"], "hpMax": b["hp_max"],
         "alive": b["alive"], "chest": b["chest"]}
        for b in gs.bosses
    ])


def board_cells_event(gs, etype, cells, **data):
    """Generic: a list of cells with the symbol now in them."""
    emit(gs, etype, cells=[
        {**pos(gs, c, r), "symbol": gs.board[c][r].name if gs.board[c][r] is not None else None,
         **({"value": _value(gs.board[c][r])} if _value(gs.board[c][r]) else {})}
        for c, r in cells
    ], **data)


def reveal(gs):
    """SDK reveal plus each weapon's damage factor, so the board can show it before it fires."""
    reveal_event(gs)
    board = gs.book.events[-1]["board"]
    for c, col in enumerate(gs.board):
        for r, sym in enumerate(col):
            if _value(sym):
                board[c][_row(gs, r)]["value"] = _value(sym)
