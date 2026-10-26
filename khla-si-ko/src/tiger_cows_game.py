from __future__ import annotations

from dataclasses import dataclass, field

BOARD_SIZE = 4
COW_COUNT = 12
TIGER = "T"
COW = "C"
EMPTY = None
PositionKey = tuple[tuple[str | None, ...], str, int, int]


def _neighbors(node: int) -> tuple[int, ...]:
    row, column = divmod(node, BOARD_SIZE)
    result = []
    if row > 0:
        result.append(node - BOARD_SIZE)
    if row < BOARD_SIZE - 1:
        result.append(node + BOARD_SIZE)
    if column > 0:
        result.append(node - 1)
    if column < BOARD_SIZE - 1:
        result.append(node + 1)
    return tuple(result)


@dataclass
class TigerCowsGame:
    board: list[str | None] = field(default_factory=lambda: [EMPTY] * (BOARD_SIZE * BOARD_SIZE))
    turn: str = "cows"
    cows_placed: int = 0
    cows_captured: int = 0
    selected_node: int | None = None
    winner: str | None = None
    status: str = "Cows go first: place a cow on a glowing square."
    move_count: int = 0
    last_move: tuple[int, int, str] | None = None
    position_counts: dict[PositionKey, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        for node in (0, BOARD_SIZE - 1, BOARD_SIZE * (BOARD_SIZE - 1), BOARD_SIZE * BOARD_SIZE - 1):
            self.board[node] = TIGER
        self._record_position()

    @property
    def game_over(self) -> bool:
        return self.winner is not None

    @property
    def cows_remaining(self) -> int:
        return COW_COUNT - self.cows_placed

    def reset(self) -> None:
        self.board = [EMPTY] * (BOARD_SIZE * BOARD_SIZE)
        for node in (0, BOARD_SIZE - 1, BOARD_SIZE * (BOARD_SIZE - 1), BOARD_SIZE * BOARD_SIZE - 1):
            self.board[node] = TIGER
        self.turn = "cows"
        self.cows_placed = 0
        self.cows_captured = 0
        self.selected_node = None
        self.winner = None
        self.status = "Cows go first: place a cow on a glowing square."
        self.last_move = None
        self.position_counts.clear()
        self._record_position()

    def legal_targets(self, source: int) -> tuple[int, ...]:
        if not 0 <= source < len(self.board):
            return ()
        piece = self.board[source]
        if piece not in (TIGER, COW):
            return ()

        targets = [node for node in _neighbors(source) if self.board[node] is EMPTY]
        if piece == TIGER:
            row, column = divmod(source, BOARD_SIZE)
            for row_step, column_step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                middle_row = row + row_step
                middle_column = column + column_step
                target_row = row + 2 * row_step
                target_column = column + 2 * column_step
                if not (0 <= target_row < BOARD_SIZE and 0 <= target_column < BOARD_SIZE):
                    continue
                middle = middle_row * BOARD_SIZE + middle_column
                target = target_row * BOARD_SIZE + target_column
                if self.board[middle] == COW and self.board[target] is EMPTY:
                    targets.append(target)
        return tuple(targets)

    def click_node(self, node: int) -> bool:
        if not 0 <= node < len(self.board) or self.game_over:
            return False

        if self.turn == "cows" and self.cows_remaining > 0:
            return self._place_cow(node)
        return self._select_or_move(node)

    def _place_cow(self, node: int) -> bool:
        if self.board[node] is not EMPTY:
            self.status = "Choose an empty square to place a cow."
            return False
        self.board[node] = COW
        self.cows_placed += 1
        self.selected_node = None

        if not self._has_legal_tiger_move():
            self.winner = "Cows"
            self.status = "Cows win! All tigers are trapped."
            return True

        self.turn = "tigers"
        self.status = "Tigers' turn: select a tiger, then a green square."
        self._record_position()
        return True

    def _select_or_move(self, node: int) -> bool:
        piece = TIGER if self.turn == "tigers" else COW
        if node == self.selected_node:
            self.selected_node = None
            self.status = f"Selection canceled. Choose one of your {'tigers' if piece == TIGER else 'cows'}."
            return True

        if self.selected_node is None:
            if self.board[node] == piece:
                self.selected_node = node
                self.status = "Piece selected. Choose a green square to move."
                return True
            self.status = f"Select one of your {'tigers' if piece == TIGER else 'cows'} first."
            return False

        if self.board[node] == piece:
            self.selected_node = node
            self.status = "Piece selected. Choose a green square to move."
            return True

        targets = self.legal_targets(self.selected_node)
        if node not in targets:
            self.status = "That move is not allowed. Choose a green highlighted square."
            return False

        source = self.selected_node
        self.move_count += 1
        self.last_move = (source, node, piece)
        captured_node = None
        if piece == TIGER and abs(node - source) in (2, BOARD_SIZE * 2):
            captured_node = (node + source) // 2
            self.board[captured_node] = EMPTY
            self.cows_captured += 1

        self.board[node] = piece
        self.board[source] = EMPTY
        self.selected_node = None

        if piece == TIGER:
            if self.cows_captured >= COW_COUNT:
                self.winner = "Tigers"
                self.status = f"Tigers win! They captured all {COW_COUNT} cows."
                return True
            self.turn = "cows"
            if self.cows_remaining == 0 and not self._has_legal_cow_move():
                self.winner = "Tigers"
                self.status = "Tigers win! All cows are trapped."
                return True
            self.status = "Cows' turn: place a cow." if self.cows_remaining else "Cows' turn: select a cow to move."
            self._record_position()
            return True

        if not self._has_legal_tiger_move():
            self.winner = "Cows"
            self.status = "Cows win! All tigers are trapped."
            return True
        self.turn = "tigers"
        self.status = "Tigers' turn: select a tiger, then a green square."
        self._record_position()
        return True

    def _record_position(self) -> None:
        position: PositionKey = (
            tuple(self.board),
            self.turn,
            self.cows_placed,
            self.cows_captured,
        )
        occurrences = self.position_counts.get(position, 0) + 1
        self.position_counts[position] = occurrences
        if occurrences >= 3:
            self.winner = "Draw"
            self.selected_node = None
            self.status = "Draw! The same board position occurred three times."

    def _has_legal_tiger_move(self) -> bool:
        return any(self.board[node] == TIGER and self.legal_targets(node) for node in range(len(self.board)))

    def _has_legal_cow_move(self) -> bool:
        return any(
            self.board[node] == COW
            and any(self.board[target] is EMPTY for target in _neighbors(node))
            for node in range(len(self.board))
        )
