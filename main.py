"""Chess Arena: visual comparison of Minimax and Alpha-Beta search trees."""
import math
import queue
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pygame
import chess
from ai import analyze_candidates, choose_varied_candidate
from comparison_ai import SearchCancelled, run_comparison, search_position
from game_logic import (legal_targets as game_legal_targets, material_balance, new_game,
                        new_randomized_game, new_random_reachable_position,
                        play_human_move, san_history, undo_last_turn)

WIDTH, HEIGHT = 1440, 900
MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT = 1120, 720
BG = (15, 19, 29)
PANEL = (25, 32, 46)
PANEL2 = (31, 40, 57)
BORDER = (57, 70, 91)
TEXT = (236, 241, 249)
MUTED = (177, 190, 207)
BLUE = (91, 177, 255)
GREEN = (65, 207, 148)
RED = (239, 91, 111)
GOLD = (255, 198, 88)
PURPLE = (174, 139, 255)


_position_random = random.SystemRandom()
_comparison_position_number = 0
MATCH_DEPTH = 2
DIFFICULTY_DEPTHS = {"Easy": 2, "Medium": 6, "Hard": 10}
selected_difficulty = "Medium"
SIMULATION_DEPTH = 2


def new_comparison_position():
    """Choose a fresh, legal middlegame reached by randomized legal play."""
    global _comparison_position_number
    board = new_random_reachable_position(_position_random, min_plies=18, max_plies=40)
    _comparison_position_number += 1
    return board, f"Random midgame {_comparison_position_number}"


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Chess Arena | Minimax vs Alpha-Beta")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("segoeui", 18)
SMALL = pygame.font.SysFont("segoeui", 15)
TINY = pygame.font.SysFont("segoeui", 13)
MED = pygame.font.SysFont("segoeui", 21, bold=True)
TITLE = pygame.font.SysFont("segoeui", 31, bold=True)
BIG = pygame.font.SysFont("segoeui", 27, bold=True)

search_depth = MATCH_DEPTH
result = None
busy = False
message = "Ready — click Run comparison."
worker = queue.Queue()
buttons = {}
tree_hitboxes = []
selected_node = None
mode = "menu"
game_board = new_game()
comparison_board, comparison_name = new_comparison_position()
stockfish_depth = 10
tree_selection = None
history_scroll = 0
engine_thread = None
comparison_view = "dashboard"
match_boards = {"minimax": chess.Board(), "alpha_beta": chess.Board()}
match_game_board = chess.Board()
match_stats = {}
match_running = False
simulation_active = False
match_message = "Ready to visualize the actual Minimax and Alpha-Beta search paths."
match_active_algorithm = None
match_searching_algorithms = set()
match_cursor_bounds = {"minimax": (None, None), "alpha_beta": (None, None)}
match_queue = queue.Queue()
match_thread = None
match_cancel = None
match_pending_acks = []
match_ack_release_at = 0.0
match_start_ply = 0
match_preview_active = False
match_preview_groups = []
match_preview_index = 0
match_preview_next_at = 0.0
match_preview_done_ack = None
MATCH_PREVIEW_INTERVAL = 0.42
MATCH_ACK_INTERVAL = 0.025
PIECE_GLYPHS = {
    (chess.WHITE, chess.KING): "♔", (chess.WHITE, chess.QUEEN): "♕", (chess.WHITE, chess.ROOK): "♖",
    (chess.WHITE, chess.BISHOP): "♗", (chess.WHITE, chess.KNIGHT): "♘", (chess.WHITE, chess.PAWN): "♙",
    (chess.BLACK, chess.KING): "♚", (chess.BLACK, chess.QUEEN): "♛", (chess.BLACK, chess.ROOK): "♜",
    (chess.BLACK, chess.BISHOP): "♝", (chess.BLACK, chess.KNIGHT): "♞", (chess.BLACK, chess.PAWN): "♟"}
PIECE_FONTS = {}
def board_pixel_size(width, height):
    return max(200, min(620, height - 155, width - 400))


def draw_chessboard(board, left, top, board_size, targets=(), selected=None, candidate_moves=()):
    square = board_size // 8
    if square not in PIECE_FONTS:
        PIECE_FONTS[square] = pygame.font.SysFont("segoeuisymbol", max(28, square - 10))
    piece_font = PIECE_FONTS[square]
    light, dark = (222, 214, 195), (91, 119, 135)
    for rank in range(8):
        for file in range(8):
            sq = chess.square(file, 7 - rank)
            rect = pygame.Rect(left + file * square, top + rank * square, square, square)
            color = light if (file + rank) % 2 == 0 else dark
            if board.move_stack and sq in (board.peek().from_square, board.peek().to_square):
                color = (199, 177, 103) if color == light else (139, 146, 85)
            if board.is_check() and board.king(board.turn) == sq:
                color = (183, 75, 82)
            if sq == selected:
                color = (227, 191, 86)
            pygame.draw.rect(screen, color, rect)
            if sq in targets:
                pygame.draw.circle(screen, (60, 170, 118), rect.center, max(6, square // 10))
            piece = board.piece_at(sq)
            if piece:
                glyph = piece_font.render(PIECE_GLYPHS[(piece.color, piece.piece_type)], True,
                                          (247, 247, 238) if piece.color else (23, 29, 38))
                screen.blit(glyph, glyph.get_rect(center=rect.center))
    # Numbered source/target markers tie the board's candidate moves to the RHS list.
    rank_colors = [GOLD, BLUE, GREEN, PURPLE, (255, 128, 91), (87, 211, 220),
                   (239, 119, 176), (175, 205, 105), (255, 153, 204)]
    for index, move_text in enumerate(candidate_moves):
        try:
            move = chess.Move.from_uci(move_text)
        except (TypeError, ValueError):
            continue
        color = rank_colors[index % len(rank_colors)]
        source = pygame.Rect(left + chess.square_file(move.from_square) * square,
                             top + (7 - chess.square_rank(move.from_square)) * square, square, square)
        target = pygame.Rect(left + chess.square_file(move.to_square) * square,
                             top + (7 - chess.square_rank(move.to_square)) * square, square, square)
        pygame.draw.rect(screen, color, source.inflate(-6, -6), width=max(2, square // 22), border_radius=5)
        pygame.draw.circle(screen, color, target.center, max(10, square // 4), width=max(2, square // 22))
        badge = pygame.Rect(target.right - max(19, square // 3), target.y + 2,
                            max(17, square // 3), max(17, square // 3))
        pygame.draw.circle(screen, (18, 23, 34), badge.center, badge.width // 2 + 1)
        pygame.draw.circle(screen, color, badge.center, badge.width // 2)
        number = TINY.render(str(index + 1), True, (18, 23, 34))
        screen.blit(number, number.get_rect(center=badge.center))
selected_square = None
legal_targets = []
engine_busy = False
engine_queue = queue.Queue()
game_message = "Your move — White to play."
minimax_busy = False
minimax_queue = queue.Queue()
minimax_thread = None
minimax_cancel = None
minimax_result = None
minimax_candidates = []
minimax_root_fen = None
minimax_apply_at = 0.0
minimax_progress = (0, 0, 0, 0, 0.0)


def draw_text(surface, value, x, y, font=FONT, color=TEXT):
    image = font.render(str(value), True, color)
    surface.blit(image, (int(x), int(y)))


def centered(surface, value, x, y, font=FONT, color=TEXT):
    image = font.render(str(value), True, color)
    surface.blit(image, (int(x - image.get_width() / 2), int(y)))


def rounded(surface, rect, color=PANEL, border=BORDER, radius=12):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)


def button(key, rect, label, active=False, enabled=True):
    color = (48, 75, 106) if active else (38, 47, 65)
    edge = BLUE if active else BORDER
    if not enabled:
        color, edge = (30, 36, 48), (43, 51, 66)
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, edge, rect, width=1, border_radius=8)
    centered(screen, label, rect.centerx, rect.y + 9, FONT, TEXT if enabled else MUTED)
    buttons[key] = rect


def start_comparison():
    global busy, result, message
    if busy or match_running:
        return
    busy, result = True, None
    depth_snapshot = search_depth
    position_snapshot = comparison_board.copy(stack=True)
    progress_state = {"started": pygame.time.get_ticks()}
    message = f"Running Minimax at depth {depth_snapshot}..."
    def task():
        try:
            def report(name, visited, leaves, cutoffs, pruned):
                worker.put(("progress", (name, visited, leaves, cutoffs, pruned, progress_state["started"])))
            worker.put(("ok", run_comparison(position_snapshot, depth=depth_snapshot, progress=report)))
        except Exception as exc:
            worker.put(("error", str(exc)))
    threading.Thread(target=task, daemon=True).start()


def legal_move_preview_groups(board):
    """Group every legal destination by the piece that can make the move."""
    grouped = {}
    for move in board.legal_moves:
        grouped.setdefault(move.from_square, []).append(move)
    return [
        {"square": square, "piece": board.piece_at(square).symbol().upper(),
         "targets": sorted({move.to_square for move in moves}), "move_count": len(moves)}
        for square, moves in grouped.items()
    ]


def move_preview_message(groups, index):
    group = groups[index]
    square = chess.square_name(group["square"])
    return (f"Legal move preview {index + 1}/{len(groups)}: "
            f"{group['piece']} on {square}, {group['move_count']} legal move(s) "
            f"to {len(group['targets'])} square(s).")


def start_parallel_games():
    global match_running, match_message, match_boards, match_game_board, match_stats, match_cancel, match_thread, comparison_view, match_active_algorithm, match_start_ply, match_preview_active, match_preview_groups, match_preview_index, match_preview_done_ack
    if match_running or busy:
        return
    comparison_view = "match"
    match_game_board = comparison_board.copy(stack=True)
    match_start_ply = match_game_board.ply()
    match_boards = {"minimax": match_game_board.copy(stack=True),
                    "alpha_beta": match_game_board.copy(stack=True)}
    match_stats = {
        key: {"nodes_visited": 0, "leaf_nodes_evaluated": 0, "cutoffs": 0,
              "pruned_moves": 0, "elapsed": 0.0, "wall_time": 0.0, "current": (0, 0, 0, 0, 0.0),
              "turn_done": False, "last_search_wall_time": 0.0, "last_search_pruned": 0,
              "moves": 0, "last_move": "—", "last_score": None}
        for key in ("minimax", "alpha_beta")
    }
    match_cursor_bounds.update({"minimax": (None, None), "alpha_beta": (None, None)})
    match_active_algorithm = None
    match_searching_algorithms.clear()
    match_preview_active = False
    match_preview_groups = []
    match_preview_index = 0
    match_preview_done_ack = None
    match_cancel = threading.Event()
    cancel_event = match_cancel
    depth_snapshot = MATCH_DEPTH
    match_running = True
    match_message = f"New {comparison_name}: {len(match_game_board.piece_map())} pieces • depth {depth_snapshot}. Previewing legal moves first."

    def task():
        game = comparison_board.copy(stack=True)

        def run_algorithm(key, root, root_fen):
            started = time.perf_counter()

            def progress(visited, leaves, cutoffs, pruned):
                if cancel_event.is_set():
                    raise SearchCancelled()
                match_queue.put(("match_progress", (key, visited, leaves, cutoffs,
                                                      pruned, time.perf_counter() - started)))

            def on_node(fen, path, ply, alpha, beta, visited, leaves, cutoffs, pruned):
                if cancel_event.is_set():
                    raise SearchCancelled()
                now = time.perf_counter()
                acknowledgement = threading.Event()
                match_queue.put(("match_cursor", (key, root_fen, path, ply, alpha, beta,
                    visited, leaves, cutoffs, pruned, now - started, acknowledgement)))
                while not acknowledgement.wait(0.05):
                    if cancel_event.is_set():
                        raise SearchCancelled()

            try:
                result = search_position(root, depth_snapshot, key, progress=progress, on_node=on_node)
                result["wall_time"] = time.perf_counter() - started
                return result
            except Exception:
                cancel_event.set()
                raise

        try:
            while not game.is_game_over(claim_draw=True):
                if cancel_event.is_set():
                    raise SearchCancelled()
                root = game.copy(stack=True)
                root_fen = root.fen()
                results = {}
                preview_done = threading.Event()
                match_queue.put(("move_preview", (root_fen, legal_move_preview_groups(root), preview_done)))
                while not preview_done.wait(0.05):
                    if cancel_event.is_set():
                        raise SearchCancelled()
                match_queue.put(("turn_start", (root_fen, root.ply())))
                for key in ("minimax", "alpha_beta"):
                    match_queue.put(("search_started", (key, root_fen)))
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="chess-search") as executor:
                    futures = {
                        executor.submit(run_algorithm, key, root.copy(stack=True), root_fen): key
                        for key in ("minimax", "alpha_beta")
                    }
                    for future in as_completed(futures):
                        key = futures[future]
                        result = future.result()
                        if cancel_event.is_set():
                            raise SearchCancelled()
                        results[key] = result
                        match_queue.put(("search_done", (key, result["best_move"], result["best_move_san"],
                            {name: result[name] for name in
                             ("nodes_visited", "leaf_nodes_evaluated", "cutoffs", "pruned_moves", "elapsed", "wall_time", "best_score")})))
                minimax_result, alpha_result = results["minimax"], results["alpha_beta"]
                if minimax_result["best_score"] != alpha_result["best_score"]:
                    raise RuntimeError("Minimax and Alpha-Beta scores disagreed; game stopped for integrity.")
                if minimax_result["best_move"] is None:
                    break
                move = chess.Move.from_uci(minimax_result["best_move"])
                san = game.san(move)
                game.push(move)
                match_queue.put(("game_move", (move.uci(), san, game.fen(), game.ply())))
            outcome = game.outcome(claim_draw=True)
            match_queue.put(("match_done", (game.result(claim_draw=True),
                                               outcome.termination.name if outcome else "unknown")))
        except SearchCancelled:
            match_queue.put(("match_cancelled", None))
        except Exception as exc:
            match_queue.put(("match_error", str(exc)))

    match_thread = threading.Thread(target=task, name="chess-arena-parallel-games", daemon=False)
    match_thread.start()


def stop_parallel_games():
    global match_message, match_preview_active, match_preview_done_ack
    if match_running and match_cancel:
        match_cancel.set()
        if match_preview_done_ack:
            match_preview_done_ack.set()
        match_preview_active = False
        match_message = "Stopping after the current search checkpoint…"


def reset_parallel_games():
    global match_boards, match_game_board, match_stats, match_message, match_active_algorithm, match_start_ply, match_preview_active, match_preview_groups, match_preview_index, match_preview_done_ack
    match_game_board = comparison_board.copy(stack=True)
    match_start_ply = match_game_board.ply()
    match_boards = {"minimax": match_game_board.copy(stack=True),
                    "alpha_beta": match_game_board.copy(stack=True)}
    match_stats = {
        key: {"nodes_visited": 0, "leaf_nodes_evaluated": 0, "cutoffs": 0,
              "pruned_moves": 0, "elapsed": 0.0, "wall_time": 0.0, "current": (0, 0, 0, 0, 0.0),
              "turn_done": False, "last_search_wall_time": 0.0, "last_search_pruned": 0,
              "moves": 0, "last_move": "—", "last_score": None}
        for key in ("minimax", "alpha_beta")
    }
    match_message = "Shared game and both search cursors reset to the selected starting position."
    match_active_algorithm = None
    match_preview_active = False
    match_preview_groups = []
    match_preview_index = 0
    if match_preview_done_ack:
        match_preview_done_ack.set()
    match_preview_done_ack = None
    match_searching_algorithms.clear()
    match_cursor_bounds.update({"minimax": (None, None), "alpha_beta": (None, None)})


def fit(value, font, max_width):
    value = str(value)
    while value and font.size(value)[0] > max_width:
        value = value[:-1]
    return value if len(value) == len(str(value)) and font.size(value)[0] <= max_width else value + "…"


def explain_trace_node(node):
    score = node.get("score")
    value = "unevaluated" if score is None else format_search_score(score)
    if node["kind"] == "pruned":
        return f"{node.get('san')} was skipped after an Alpha-Beta cutoff; its branch could not change the minimax choice."
    if node.get("cutoff"):
        return f"Cutoff at this node: α={node.get('alpha')} and β={node.get('beta')}; remaining moves were skipped."
    if node["kind"] == "leaf":
        return f"Leaf at ply {node['depth']}: the shared evaluator returned {value}; this score propagates to its parent."
    if node["kind"] == "root":
        return f"Root position: search compares legal continuations and chooses the best returned score ({value})."
    return f"Move {node.get('san')} was searched; its continuation returned {value} to the parent."


def format_search_score(score):
    if abs(score) >= 99_000:
        return f"{'+' if score > 0 else '−'}MATE ({score:+,})"
    return f"{score:+,} cp"


def format_game_outcome(board):
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return "Game in progress"
    if outcome.termination == chess.Termination.STALEMATE:
        return "Draw — stalemate"
    if outcome.winner is None:
        reason = outcome.termination.name.replace("_", " ").lower()
        return f"Draw — {reason}"
    winner = "White" if outcome.winner == chess.WHITE else "Black"
    reason = outcome.termination.name.replace("_", " ").lower()
    return f"{winner} wins — {reason}"


def draw_card(rect, label, value, subtitle, accent):
    rounded(screen, rect, PANEL2)
    draw_text(screen, label.upper(), rect.x + 13, rect.y + 9, TINY, MUTED)
    draw_text(screen, value, rect.x + 13, rect.y + 27, BIG, accent)
    draw_text(screen, subtitle, rect.x + 13, rect.bottom - 23, SMALL, MUTED)


def draw_tree(rect, trace, title, accent):
    global tree_hitboxes
    rounded(screen, rect, PANEL)
    draw_text(screen, title, rect.x + 14, rect.y + 12, MED, accent)
    draw_text(screen, f"{trace['nodes_evaluated']:,} evaluated leaves", rect.x + 14, rect.y + 39, SMALL, MUTED)
    content = pygame.Rect(rect.x + 10, rect.y + 65, rect.width - 20, rect.height - 76)
    pygame.draw.rect(screen, (17, 22, 33), content, border_radius=8)
    nodes = trace["nodes"]
    # Limit drawn nodes to keep the interface responsive; all metrics use full trace.
    visible = nodes[:min(220, len(nodes))]
    visible_ids = {n["id"] for n in visible}
    max_depth = max((n["depth"] for n in nodes), default=1)
    levels = {}
    for node in visible:
        levels.setdefault(node["depth"], []).append(node)
    positions = {}
    for d, level in levels.items():
        x = content.x + 25 + (content.width - 50) * d / max(1, max_depth)
        gap = min(24, (content.height - 24) / max(1, len(level)))
        start_y = content.centery - gap * (len(level) - 1) / 2
        for i, node in enumerate(level):
            positions[node["id"]] = (int(x), int(start_y + i * gap))
    # Draw links only when both endpoints are visible.
    for parent, child in trace["edges"]:
        if parent in positions and child in positions:
            pygame.draw.line(screen, (66, 78, 99), positions[parent], positions[child], 1)
    for node in visible:
        x, y = positions[node["id"]]
        kind = node["kind"]
        selected = tree_selection == (trace["algorithm"], node["id"])
        color = GOLD if selected else RED if kind == "pruned" else GREEN if kind == "leaf" else accent
        radius = 5 if kind == "root" else 3
        pygame.draw.circle(screen, color, (x, y), radius)
        tree_hitboxes.append((pygame.Rect(x - 7, y - 7, 14, 14), trace["algorithm"], node))
        if node["depth"] == max_depth or kind == "pruned" or kind == "root":
            label = "ROOT" if kind == "root" else node.get("san", "")
            if kind == "pruned":
                label = "× " + label
            if label:
                draw_text(screen, label[:12], x + 5, y - 8, TINY, RED if kind == "pruned" else MUTED)
    if len(nodes) > len(visible):
        draw_text(screen, f"Drawing {len(visible)} / {len(nodes):,} recorded nodes", content.x + 8, content.bottom - 17, TINY, MUTED)


def draw():
    global buttons, tree_hitboxes
    buttons = {}
    tree_hitboxes = []
    screen.fill(BG)
    w, h = screen.get_size()
    margin = 20
    if mode == "menu":
        centered(screen, "CHESS ARENA", w // 2, int(h * .13), TITLE)
        centered(screen, "Chess AI and search algorithm visualization platform", w // 2, int(h * .18), FONT, MUTED)
        for key, label, sub, y, accent in [
            ("play", "PLAY WITH AI", "Play a legal chess game against Stockfish", int(h * .26), BLUE),
            ("compare", "ALGORITHM COMPARISON", "Compare real Minimax and Alpha-Beta searches", int(h * .39), GREEN)]:
            card_w = min(460, w - 40)
            rect = pygame.Rect((w - card_w) // 2, y, card_w, 88)
            rounded(screen, rect, PANEL2)
            pygame.draw.rect(screen, accent, rect, 2, border_radius=12)
            centered(screen, label, w // 2, y + 17, MED, accent)
            centered(screen, sub, w // 2, y + 52, SMALL, MUTED)
            buttons[key] = rect
        button("settings", pygame.Rect(w // 2 - 120, int(h * .53), 110, 40), "Settings")
        button("exit", pygame.Rect(w // 2 + 10, int(h * .53), 110, 40), "Exit")
        centered(screen, "Play mode: human vs Stockfish.  Comparison mode: inspect the custom search algorithms.",
                 w // 2, int(h * .65), SMALL, MUTED)
        return
    if mode == "difficulty":
        centered(screen, "CHOOSE YOUR DIFFICULTY", w // 2, int(h * .17), TITLE)
        centered(screen, "Choose how deeply Stockfish searches before the game starts.",
                 w // 2, int(h * .24), FONT, MUTED)
        gap = 14
        card_w = min(250, (w - 80 - 2 * gap) // 3)
        card_y, card_h = int(h * .34), 135
        total_w = 3 * card_w + 2 * gap
        start_x = (w - total_w) // 2
        for index, (level, depth) in enumerate(DIFFICULTY_DEPTHS.items()):
            rect = pygame.Rect(start_x + index * (card_w + gap), card_y, card_w, card_h)
            rounded(screen, rect, PANEL2, BLUE if selected_difficulty == level else BORDER)
            if selected_difficulty == level:
                pygame.draw.rect(screen, BLUE, rect, width=2, border_radius=12)
            centered(screen, level.upper(), rect.centerx, rect.y + 24, MED,
                     BLUE if selected_difficulty == level else TEXT)
            centered(screen, f"Search depth {depth}", rect.centerx, rect.y + 66, FONT, MUTED)
            centered(screen, {"Easy": "Good for a relaxed game", "Medium": "A balanced challenge",
                              "Hard": "Strongest setting"}[level],
                     rect.centerx, rect.y + 99, TINY, MUTED)
            buttons[f"difficulty_{level.lower()}"] = rect
        centered(screen, "Difficulty changes Stockfish's search depth; it is not a fixed Elo rating.",
                 w // 2, card_y + card_h + 28, SMALL, MUTED)
        button("start_game", pygame.Rect(w // 2 - 115, int(h * .66), 230, 46),
               f"Start Game • {selected_difficulty}", active=True)
        button("difficulty_back", pygame.Rect(w // 2 - 95, int(h * .75), 190, 40), "Back to Menu")
        return
    if mode == "settings":
        centered(screen, "SETTINGS", w // 2, int(h * .16), TITLE)
        centered(screen, "Stockfish difficulty is a search depth, not an Elo rating.", w // 2, int(h * .22), FONT, MUTED)
        centered(screen, f"Stockfish depth: {stockfish_depth}", w // 2, int(h * .31), MED, BLUE)
        button("sf_minus", pygame.Rect(w // 2 - 110, int(h * .36), 48, 40), "−")
        button("sf_plus", pygame.Rect(w // 2 + 62, int(h * .36), 48, 40), "+")
        centered(screen, f"Comparison depth: {search_depth} (maximum 4)", w // 2, int(h * .47), MED, GREEN)
        button("cmp_minus", pygame.Rect(w // 2 - 110, int(h * .52), 48, 40), "−")
        button("cmp_plus", pygame.Rect(w // 2 + 62, int(h * .52), 48, 40), "+")
        button("menu", pygame.Rect(w // 2 - 100, int(h * .63), 200, 42), "Return to Menu")
        return
    if mode == "play":
        draw_play_screen(w, h)
        return
    if comparison_view == "match":
        draw_match_screen(w, h)
        return
    draw_text(screen, "CHESS ARENA", margin, 14, TITLE)
    draw_text(screen, "Algorithm Visualization Lab  •  Plain Minimax vs Alpha-Beta Pruning", margin + 2, 48, SMALL, MUTED)
    button("match", pygame.Rect(w - 330, 18, 150, 35),
           "View live search" if match_running else "Visualize game", active=match_running,
           enabled=match_running or not busy)
    if match_running:
        button("stop_match", pygame.Rect(w - 495, 18, 150, 35), "Stop games", enabled=True)
    button("menu", pygame.Rect(w - 165, 18, 145, 35), "Return to Menu", enabled=not busy and not match_running)
    draw_text(screen, fit(message, SMALL, w - 2 * margin), margin, 75, SMALL,
              GOLD if busy else GREEN if result else MUTED)
    controls_enabled = not busy and not match_running
    button("minus", pygame.Rect(margin, 101, 42, 35), "−", enabled=controls_enabled)
    button("depth", pygame.Rect(margin + 49, 101, 120, 35), f"Depth: {search_depth}", enabled=False)
    button("plus", pygame.Rect(margin + 176, 101, 42, 35), "+", enabled=controls_enabled)
    button("run", pygame.Rect(margin + 230, 101, 175, 35), "Running..." if busy else "Run comparison", active=True, enabled=controls_enabled)
    button("reset", pygame.Rect(margin + 416, 101, 115, 35), "Reset", enabled=controls_enabled)
    position_y = 101 if w >= 1200 else 143
    position_x = 560 if w >= 1200 else 20
    button("midgame", pygame.Rect(position_x, position_y, 180, 35), "New random position", enabled=controls_enabled)
    if w >= 1200:
        draw_text(screen, fit("Random legal midgame • both searches share this preview", SMALL, w - 755),
                  750, 111, SMALL, MUTED)
    else:
        draw_text(screen, fit("Random legal midgame • preview below", SMALL, w - 40), 20, 179, SMALL, MUTED)
    gap = 12
    compact = w < 1200
    card_y, card_h = (196 if compact else 150), 78
    card_w = (w - 2 * margin - 3 * gap) // 4
    if result:
        s = result["summary"]
        min_score = result["minimax"]["best_score"]
        ab_score = result["alpha_beta"]["best_score"]
        speed_reliable = s["minimax_time"] >= 0.01 and s["alpha_beta_time"] >= 0.01
        speed_value = f"{s['minimax_time'] / s['alpha_beta_time']:.2f}×" if speed_reliable else "—"
        speed_sub = f"{s['minimax_time']:.3f}s vs {s['alpha_beta_time']:.3f}s" if speed_reliable else "Timing too short to compare reliably"
        cards = [("Minimax evaluated leaves", f"{s['minimax_nodes']:,}", f"{result['minimax']['nodes_visited']:,} visited • {format_search_score(min_score)}", BLUE),
                 ("Alpha-Beta evaluated leaves", f"{s['alpha_beta_nodes']:,}", f"{result['alpha_beta']['nodes_visited']:,} visited • {format_search_score(ab_score)}", GREEN),
                 ("Leaf reduction", f"{s['node_reduction_percent']:.2f}%", f"{s['pruned_moves']:,} legal moves skipped", GOLD),
                 ("Runtime speedup", speed_value, speed_sub, PURPLE)]
    else:
        cards = [("Minimax nodes", "—", "Plain exhaustive search", BLUE), ("Alpha-Beta nodes", "—", "Search with cutoffs", GREEN), ("Node reduction", "—", "Appears after run", GOLD), ("Runtime speedup", "—", "Appears after run", PURPLE)]
    for i, args in enumerate(cards):
        draw_card(pygame.Rect(margin + i * (card_w + gap), card_y, card_w, card_h), *args)

    tree_top = 291 if compact else 245
    footer_h = 62
    tree_h = max(140, h - tree_top - footer_h - 22)
    tree_w = (w - 2 * margin - gap) // 2
    left = pygame.Rect(margin, tree_top, tree_w, tree_h)
    right = pygame.Rect(margin + tree_w + gap, tree_top, tree_w, tree_h)
    if result:
        draw_tree(left, result["minimax"], "PLAIN MINIMAX", BLUE)
        draw_tree(right, result["alpha_beta"], "MINIMAX + ALPHA-BETA", GREEN)
    else:
        for rect, title, accent, sub in [(left, "PLAIN MINIMAX", BLUE, "All branches explored to the selected depth"), (right, "MINIMAX + ALPHA-BETA", GREEN, "Cutoffs and pruned branches shown in red")]:
            rounded(screen, rect)
            draw_text(screen, title, rect.x + 18, rect.y + 14, MED, accent)
            draw_text(screen, fit(f"Visible start: {comparison_name}", SMALL, rect.width - 36),
                      rect.x + 18, rect.y + 50, SMALL, MUTED)
            preview_size = max(100, min(220, rect.width - 48, rect.height - 145))
            preview_x = rect.centerx - preview_size // 2
            preview_y = rect.y + 82
            draw_chessboard(comparison_board, preview_x, preview_y, preview_size)
            centered(screen, "Both searches use this same position", rect.centerx,
                     preview_y + preview_size + 18, SMALL, TEXT)
            centered(screen, sub, rect.centerx, preview_y + preview_size + 44, TINY, MUTED)
    footer = pygame.Rect(margin, h - footer_h - 10, w - 2 * margin, footer_h)
    rounded(screen, footer)
    draw_text(screen, "LEGEND", footer.x + 12, footer.y + 10, SMALL, MUTED)
    legend = [(BLUE, "Minimax nodes"), (GREEN, "Alpha-Beta / leaves"), (RED, "Pruned move"), (GOLD, "Controls above")]
    x = footer.x + 90
    for color, label in legend:
        pygame.draw.circle(screen, color, (x, footer.y + 19), 5)
        draw_text(screen, label, x + 10, footer.y + 10, SMALL)
        x += 190
    if result:
        s = result["summary"]
        if tree_selection:
            selected_trace = result[tree_selection[0]]
            detail = next((n for n in selected_trace["nodes"] if n["id"] == tree_selection[1]), None)
        else:
            detail = None
        if detail:
            score_text = "pending" if detail.get("score") is None else format_search_score(detail["score"])
            footer_text = (f"Selected {detail['kind']} #{detail['id']} at ply {detail['depth']} | {detail.get('san','root')} | score {score_text} | "
                           f"α={detail.get('alpha')} β={detail.get('beta')} | cutoff={detail.get('cutoff', False)}")
        else:
            footer_text = f"Scores match: {s['same_score']} | Best: {result['minimax']['best_move_san']} / {result['alpha_beta']['best_move_san']} | Click a node to inspect it."
    else:
        footer_text = "Same position • Same depth • Same evaluation • Same move ordering"
    draw_text(screen, fit(footer_text, SMALL, footer.width - 24), footer.x + 12, footer.y + 36, SMALL, MUTED)


def draw_play_screen(w, h):
    global buttons
    buttons = {}
    draw_text(screen, "PLAY WITH STOCKFISH", 24, 18, TITLE)
    draw_text(screen, f"{selected_difficulty} • Stockfish depth {stockfish_depth}", 370, 28, SMALL, BLUE)
    draw_text(screen, fit(game_message, SMALL, w - 52), 26, 58, SMALL,
              GOLD if engine_busy or minimax_busy else GREEN if game_board.is_game_over() else MUTED)
    button("new", pygame.Rect(24, 88, 125, 36), "New Game", enabled=not engine_busy and not minimax_busy and not simulation_active)
    button("undo", pygame.Rect(160, 88, 100, 36), "Undo", enabled=not engine_busy and not minimax_busy and not simulation_active and bool(game_board.move_stack))
    button("menu", pygame.Rect(271, 88, 145, 36), "Return to Menu", enabled=not engine_busy and not minimax_busy and not simulation_active)
    button("minimax", pygame.Rect(430, 88, 190, 36), "Searching…" if minimax_busy else "Minimax move  [Space]",
           active=minimax_busy, enabled=not engine_busy and not minimax_busy and not simulation_active and not game_board.is_game_over(claim_draw=True))
    button("simulate", pygame.Rect(630, 88, 170, 36),
           "Stop simulation" if simulation_active else "Simulate result",
           active=simulation_active,
           enabled=simulation_active or (not engine_busy and not minimax_busy and not game_board.is_game_over(claim_draw=True)))
    board_size = board_pixel_size(w, h)
    square = board_size // 8
    left, top = 30, 145
    board_candidates = minimax_candidates[:9] if minimax_busy or minimax_result else []
    draw_chessboard(game_board, left, top, board_size, legal_targets, selected_square,
                    [candidate["move"] for candidate in board_candidates])
    panel_x = left + board_size + 28
    draw_text(screen, "GAME", panel_x, top + 4, MED, BLUE)
    turn = "White" if game_board.turn else "Black"
    draw_text(screen, f"Turn: {turn}", panel_x, top + 40, FONT)
    balance = material_balance(game_board)
    side, advantage = ("White", balance) if balance >= 0 else ("Black", -balance)
    draw_text(screen, f"Material: {side} +{advantage}", panel_x, top + 66, SMALL, GOLD)
    if game_board.is_check() and not game_board.is_game_over(claim_draw=True):
        draw_text(screen, f"{turn} is in check", panel_x, top + 92, SMALL, RED)
    if game_board.is_game_over(claim_draw=True):
        draw_text(screen, fit(format_game_outcome(game_board), MED, max(100, w - panel_x - 24)),
                  panel_x, top + 96, MED, GOLD)
    progress_nodes, progress_leaves, progress_cutoffs, progress_pruned, progress_elapsed = minimax_progress
    draw_text(screen, "MINIMAX MOVE OPTIONS", panel_x, top + 142, MED, BLUE)
    if minimax_busy:
        draw_text(screen, f"Evaluating legal moves • depth {search_depth} • {progress_nodes:,} nodes • {progress_elapsed:.1f}s",
                  panel_x, top + 168, TINY, MUTED)
    elif not minimax_candidates:
        draw_text(screen, "Press Space or click Minimax to see its choices.", panel_x, top + 170, SMALL, MUTED)
    shown_candidates = minimax_candidates[:9] if minimax_busy or minimax_result else []
    candidate_top = top + 197
    candidate_colors = [GOLD, BLUE, GREEN, PURPLE, (255, 128, 91), (87, 211, 220),
                        (239, 119, 176), (175, 205, 105), (255, 153, 204)]
    area_w = max(100, w - panel_x - 28)
    for index, candidate in enumerate(shown_candidates):
        y = candidate_top + index * 27
        is_best = bool(minimax_result and candidate["move"] == minimax_result["best_move"])
        color = GOLD if is_best else candidate_colors[index % len(candidate_colors)]
        row_rect = pygame.Rect(panel_x, y, area_w, 24)
        rounded(screen, row_rect, (46, 43, 37) if is_best else PANEL2,
                color if is_best else BORDER, radius=6)
        pygame.draw.circle(screen, color, (panel_x + 14, y + 12), 8)
        number = TINY.render(str(index + 1), True, (18, 23, 34))
        screen.blit(number, number.get_rect(center=(panel_x + 14, y + 12)))
        move = chess.Move.from_uci(candidate["move"])
        route = f"{chess.square_name(move.from_square)} → {chess.square_name(move.to_square)}"
        score = "evaluating…" if candidate.get("score") is None else format_search_score(candidate["score"])
        detail = f"{candidate['san']}   {route}   {score}"
        if is_best:
            detail += "   BEST — PLAYING NEXT"
        draw_text(screen, fit(detail, SMALL, area_w - 34), panel_x + 29, y + 3,
                  SMALL, GOLD if is_best else TEXT)
    if minimax_busy:
        draw_text(screen, "Board markers 1–9 match these candidate moves.", panel_x, candidate_top + 9 * 27 + 4, TINY, MUTED)
    elif minimax_result:
        draw_text(screen, "Highest minimax score is marked BEST; it will be played automatically.",
                  panel_x, candidate_top + 9 * 27 + 4, TINY, GOLD)
    moves_top = top + 465
    draw_text(screen, "Moves (SAN)", panel_x, moves_top, MED)
    history = san_history(game_board)
    pairs = [(idx, history[idx], history[idx + 1] if idx + 1 < len(history) else None)
             for idx in range(0, len(history), 2)]
    start = max(0, len(pairs) - 7 - history_scroll)
    end = max(start, len(pairs) - history_scroll)
    for row, (idx, white_move, black_move) in enumerate(pairs[start:end]):
        line = f"{idx // 2 + 1}. {white_move}" + (f"   {black_move}" if black_move else "")
        draw_text(screen, line, panel_x, moves_top + 30 + row * 20, SMALL,
                  GOLD if idx + (1 if black_move else 0) == len(history) - 1 else MUTED)
    draw_text(screen, "Space or click Minimax to let the algorithm play White.", panel_x, min(h - 22, moves_top + 180), TINY, MUTED)


def draw_match_screen(w, h):
    global buttons
    buttons = {}
    draw_text(screen, "LIVE MINIMAX SEARCH PLAYBACK", 22, 15, TITLE)
    draw_text(screen, f"Depth {MATCH_DEPTH} • legal moves previewed first; both searches animate concurrently",
              24, 49, SMALL, MUTED)
    button("dashboard", pygame.Rect(w - 495, 18, 150, 35), "Analysis dashboard")
    button("match_reset", pygame.Rect(w - 660, 18, 150, 35), "New position", enabled=not match_running)
    button("match_stop", pygame.Rect(w - 330, 18, 145, 35), "Stop games" if match_running else "Games stopped",
           active=match_running, enabled=match_running)
    button("match_menu", pygame.Rect(w - 165, 18, 145, 35), "Return to Menu", enabled=not match_running)
    game_turn = "White" if match_game_board.turn else "Black"
    game_history = san_history(match_game_board)
    last_game_moves = " ".join(game_history[-8:]) if game_history else comparison_name
    draw_text(screen, fit(f"{game_turn} to move • Game: {last_game_moves}", SMALL, w - 48),
              24, 72, SMALL, GOLD)
    draw_text(screen, fit(match_message, TINY, w - 48), 24, 91, TINY,
              GOLD if match_running else GREEN)
    preview_group = (match_preview_groups[match_preview_index]
                     if match_preview_active and match_preview_index < len(match_preview_groups) else None)
    margin, gap, top = 20, 16, 116
    panel_w = (w - 2 * margin - gap) // 2
    panel_h = h - top - 16
    board_size = max(160, min(450, panel_w - 230, h - 370))
    metric_specs = (("nodes_visited", 0, "Nodes"), ("leaf_nodes_evaluated", 1, "Leaves"),
                    ("cutoffs", 2, "Cutoffs"), ("pruned_moves", 3, "Pruned"))
    metric_totals = {}
    for stat_key, tuple_index, _label in metric_specs:
        metric_totals[stat_key] = {
            key: match_stats.get(key, {}).get(stat_key, 0)
                 + match_stats.get(key, {}).get("current", (0, 0, 0, 0, 0.0))[tuple_index]
            for key in ("minimax", "alpha_beta")
        }
    for index, (key, title, accent) in enumerate((
            ("minimax", "PLAIN MINIMAX", BLUE), ("alpha_beta", "ALPHA-BETA", GREEN))):
        panel = pygame.Rect(margin + index * (panel_w + gap), top, panel_w, panel_h)
        rounded(screen, panel, PANEL)
        stats = match_stats.get(key, {})
        is_active = key in match_searching_algorithms
        if preview_group:
            panel_title = f"{title} • MOVE PREVIEW {match_preview_index + 1}/{len(match_preview_groups)}"
        elif is_active:
            panel_title = f"{title} • SEARCHING"
        elif stats.get("turn_done"):
            panel_title = f"{title} • DONE IN {stats['last_search_wall_time']:.2f}s"
        else:
            panel_title = title
        title_color = PURPLE if is_active else GREEN if stats.get("turn_done") else accent
        draw_text(screen, fit(panel_title, MED, panel.width - 32), panel.x + 16, panel.y + 12, MED, title_color)
        board_x, board_y = panel.x + 14, panel.y + 58
        draw_chessboard(match_boards[key], board_x, board_y, board_size,
                        preview_group["targets"] if preview_group else (),
                        preview_group["square"] if preview_group else None)
        info_x = board_x + board_size + 22
        info_w = max(72, panel.right - info_x - 14)
        game = match_boards[key]
        current = stats.get("current", (0, 0, 0, 0, 0.0))
        current_nodes, current_leaves, current_cutoffs, current_pruned, current_elapsed = current
        draw_text(screen, fit(f"Side to move: {'White' if game.turn else 'Black'}", SMALL, info_w),
                  info_x, board_y + 2, SMALL, MUTED)
        if stats.get("last_move", "—") != "—":
            draw_text(screen, fit(f"Last move: {stats['last_move']}", MED, info_w),
                      info_x, board_y + 29, MED, GOLD)
        if game.is_game_over(claim_draw=True):
            outcome = game.outcome(claim_draw=True)
            draw_text(screen, fit(f"Finished: {game.result(claim_draw=True)}", MED, info_w),
                      info_x, board_y + 56, MED, GOLD)
            if outcome:
                draw_text(screen, fit(outcome.termination.name.replace("_", " ").title(), TINY, info_w),
                          info_x, board_y + 82, TINY, MUTED)
        draw_text(screen, fit("SEARCH STATS • LIVE TOTAL", SMALL, info_w),
                  info_x, board_y + 111, SMALL, accent)
        for row, (stat_key, _tuple_index, label) in enumerate(metric_specs):
            y = board_y + 137 + row * 22
            value = metric_totals[stat_key][key]
            draw_text(screen, fit(f"{label}: {value:,}", SMALL, info_w), info_x, y - 2, SMALL, TEXT)
        if match_running:
            draw_text(screen, fit("Current search", SMALL, info_w), info_x, board_y + 236, SMALL, PURPLE)
            draw_text(screen, fit(f"Nodes: {current_nodes:,} • Leaves: {current_leaves:,}", TINY, info_w),
                      info_x, board_y + 258, TINY, MUTED)
            draw_text(screen, fit(f"Cutoffs: {current_cutoffs:,} • Pruned: {current_pruned:,}", TINY, info_w),
                      info_x, board_y + 278, TINY, MUTED)
        live_wall_time = stats.get("wall_time", 0.0) + (current_elapsed if match_running else 0.0)
        draw_text(screen, fit(f"Total search time: {live_wall_time:.1f}s", TINY, info_w),
                  info_x, board_y + 314, TINY, MUTED)
        draw_text(screen, f"Search time {live_wall_time:.1f}s", board_x,
                  board_y + board_size + 7, TINY, MUTED)
        time_bar = pygame.Rect(board_x, board_y + board_size + 25, board_size, 9)
        pygame.draw.rect(screen, PANEL2, time_bar, border_radius=5)
        time_fill = int(time_bar.width * min(1.0, live_wall_time / 60.0))
        if time_fill:
            pygame.draw.rect(screen, accent,
                             pygame.Rect(time_bar.x, time_bar.y, max(5, time_fill), time_bar.height),
                             border_radius=5)
        history_top = board_y + board_size + 43
        draw_text(screen, "Current branch (SAN)", board_x, history_top, SMALL, MUTED)
        history = san_history(game)
        visible_rows = min(8, max(0, (panel.bottom - history_top - 25) // 18))
        for row, move in enumerate(history[-visible_rows:] if visible_rows else []):
            ply_index = len(history) - min(visible_rows, len(history)) + row
            label = f"{ply_index // 2 + 1}. " if ply_index % 2 == 0 else "   "
            draw_text(screen, label + move, board_x, history_top + 23 + row * 18,
                      TINY, GOLD if row == min(7, len(history) - 1) else TEXT)
def request_engine_move():
    global engine_busy, game_message, engine_thread
    engine_busy = True
    depth = SIMULATION_DEPTH if simulation_active else stockfish_depth
    game_message = (f"Simulation running: Stockfish is searching at depth {depth}…"
                    if simulation_active else "Stockfish is thinking…")
    snapshot = game_board.copy(stack=True)
    def task():
        try:
            candidates = analyze_candidates(snapshot, depth=depth, multipv=4)
            chosen = choose_varied_candidate(candidates)
            if chosen:
                candidates = [chosen] + [candidate for candidate in candidates if candidate is not chosen]
            engine_queue.put(("ok", candidates))
        except Exception as exc:
            engine_queue.put(("error", str(exc)))
    engine_thread = threading.Thread(target=task, daemon=False)
    engine_thread.start()


def start_minimax_turn():
    global minimax_busy, minimax_thread, minimax_cancel, minimax_result
    global minimax_candidates, minimax_root_fen, minimax_progress, game_message
    if (mode != "play" or minimax_busy or engine_busy or simulation_active or game_board.turn != chess.WHITE
            or game_board.is_game_over(claim_draw=True)):
        return
    snapshot = game_board.copy(stack=True)
    minimax_root_fen = snapshot.fen()
    minimax_result = None
    temp = snapshot.copy(stack=False)
    minimax_candidates = [{"san": temp.san(move), "score": None, "move": move.uci()}
                          for move in temp.legal_moves]
    minimax_progress = (0, 0, 0, 0, 0.0)
    minimax_cancel = threading.Event()
    cancel_event = minimax_cancel
    depth_snapshot = search_depth
    minimax_busy = True
    game_message = f"Minimax searching at depth {depth_snapshot}…"

    def task():
        started = time.perf_counter()
        try:
            def progress(visited, leaves, cutoffs, pruned):
                if cancel_event.is_set():
                    raise SearchCancelled()
                minimax_queue.put(("progress", (visited, leaves, cutoffs, pruned,
                                                   time.perf_counter() - started)))
            result = search_position(snapshot, depth_snapshot, "minimax", progress=progress)
            minimax_queue.put(("ok", result))
        except SearchCancelled:
            minimax_queue.put(("cancelled", None))
        except Exception as exc:
            minimax_queue.put(("error", str(exc)))

    minimax_thread = threading.Thread(target=task, name="chess-arena-play-minimax", daemon=False)
    minimax_thread.start()


def main():
    global search_depth, result, busy, message, mode, screen, game_board, selected_square, legal_targets, engine_busy, game_message
    global selected_difficulty, stockfish_depth, simulation_active
    global comparison_board, comparison_name, tree_selection, history_scroll
    global comparison_view, match_running, match_message, match_game_board, match_boards, match_active_algorithm, match_cursor_bounds, match_pending_acks, match_ack_release_at
    global match_start_ply, match_preview_active, match_preview_groups, match_preview_index, match_preview_next_at, match_preview_done_ack
    global minimax_busy, minimax_cancel, minimax_result, minimax_candidates, minimax_root_fen, minimax_apply_at, minimax_progress, minimax_thread
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                simulation_active = False
            elif event.type == pygame.VIDEORESIZE:
                size = (max(MIN_WINDOW_WIDTH, event.w), max(MIN_WINDOW_HEIGHT, event.h))
                screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if mode != "menu" and not engine_busy and not minimax_busy and not busy and not match_running:
                    mode = "menu"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and mode == "play":
                start_minimax_turn()
            elif event.type == pygame.MOUSEWHEEL and mode == "play":
                max_scroll = max(0, (len(game_board.move_stack) + 1) // 2 - 9)
                history_scroll = max(0, min(max_scroll, history_scroll - event.y))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5) and mode == "play":
                max_scroll = max(0, (len(game_board.move_stack) + 1) // 2 - 9)
                history_scroll = max(0, min(max_scroll, history_scroll + (1 if event.button == 4 else -1)))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if mode == "compare" and result:
                    for hitbox, tree_key, node in tree_hitboxes:
                        if hitbox.collidepoint(event.pos):
                            tree_selection = (tree_key, node["id"])
                            message = explain_trace_node(node)
                            break
                for key, rect in list(buttons.items()):
                    if rect.collidepoint(event.pos):
                        if key == "play":
                            mode = "difficulty"
                        elif key in ("difficulty_easy", "difficulty_medium", "difficulty_hard"):
                            selected_difficulty = key.rsplit("_", 1)[-1].title()
                            stockfish_depth = DIFFICULTY_DEPTHS[selected_difficulty]
                        elif key == "start_game":
                            stockfish_depth = DIFFICULTY_DEPTHS[selected_difficulty]
                            simulation_active = False
                            mode = "play"
                            game_board = new_randomized_game(_position_random)
                            history_scroll = 0
                            game_message = "Fresh randomized opening — White to play."
                            minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                        elif key == "difficulty_back":
                            mode = "menu"
                        elif key == "compare":
                            mode = "compare"
                            comparison_view = "dashboard"
                            comparison_board, comparison_name = new_comparison_position()
                            result = None
                            tree_selection = None
                            message = f"Previewing {comparison_name}. Both algorithms will use this same position."
                        elif key == "match" and mode == "compare":
                            if match_running:
                                comparison_view = "match"
                            else:
                                start_parallel_games()
                        elif key in ("stop_match", "match_stop"):
                            stop_parallel_games()
                        elif key == "dashboard":
                            comparison_view = "dashboard"
                            if not match_running:
                                comparison_board, comparison_name = new_comparison_position()
                                message = f"Fresh position ready: {comparison_name} ({len(comparison_board.piece_map())} pieces)."
                        elif key == "match_reset" and not match_running:
                            comparison_board, comparison_name = new_comparison_position()
                            reset_parallel_games()
                            comparison_view = "dashboard"
                            message = f"Fresh {comparison_name} selected ({len(comparison_board.piece_map())} pieces). Review both boards, then start the game."
                        elif key == "match_menu" and not match_running:
                            mode = "menu"
                            comparison_view = "dashboard"
                        elif key == "settings":
                            mode = "settings"
                        elif key == "exit":
                            running = False
                        elif key == "sf_minus":
                            stockfish_depth = max(1, stockfish_depth - 1)
                        elif key == "sf_plus":
                            stockfish_depth = min(18, stockfish_depth + 1)
                        elif key == "cmp_minus":
                            search_depth = max(1, search_depth - 1)
                        elif key == "cmp_plus":
                            search_depth = min(4, search_depth + 1)
                        elif key == "minimax" and mode == "play":
                            start_minimax_turn()
                        elif key == "simulate" and mode == "play":
                            if simulation_active:
                                simulation_active = False
                                game_message = "Simulation will stop after the current Stockfish move."
                            elif not engine_busy and not minimax_busy and not game_board.is_game_over(claim_draw=True):
                                simulation_active = True
                                game_message = (f"Simulating to a real result: Stockfish plays both sides "
                                               f"at depth {SIMULATION_DEPTH}.")
                                request_engine_move()
                        elif key == "menu" and not engine_busy and not minimax_busy and not busy:
                            mode = "menu"
                            selected_square, legal_targets = None, []
                        elif key == "new" and not engine_busy and not minimax_busy:
                            simulation_active = False
                            game_board = new_randomized_game(_position_random)
                            selected_square, legal_targets = None, []
                            minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                            game_message = "Fresh randomized opening — White to play."
                        elif key == "undo" and game_board.move_stack and not engine_busy and not minimax_busy:
                            undo_last_turn(game_board)
                            selected_square, legal_targets = None, []
                            minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                            game_message = "Move undone."
                        elif key == "minus" and not busy:
                            search_depth = max(1, search_depth - 1)
                        elif key == "plus" and not busy:
                            search_depth = min(4, search_depth + 1)
                        elif key == "run" and not busy:
                            start_comparison()
                        elif key == "reset" and not busy:
                            result = None
                            tree_selection = None
                            message = f"Reset comparison view at {comparison_name}."
                        elif key == "midgame" and not busy:
                            comparison_board, comparison_name = new_comparison_position()
                            result = None
                            tree_selection = None
                            message = f"Selected a fresh legal position: {comparison_name}."
                        break
                else:
                    if mode == "play" and not engine_busy and not minimax_busy and not simulation_active and not game_board.is_game_over(claim_draw=True):
                        bx, by = 30, 145
                        sqsize = max(1, board_pixel_size(screen.get_width(), screen.get_height()) // 8)
                        file, rank_from_top = (event.pos[0] - bx) // sqsize, (event.pos[1] - by) // sqsize
                        if 0 <= file < 8 and 0 <= rank_from_top < 8 and game_board.turn == chess.WHITE:
                            target = chess.square(file, 7 - rank_from_top)
                            if selected_square is not None:
                                candidate = play_human_move(game_board, selected_square, target)
                                if candidate:
                                    selected_square, legal_targets = None, []
                                    minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                                    if game_board.is_game_over(claim_draw=True):
                                        game_message = format_game_outcome(game_board)
                                    else:
                                        request_engine_move()
                                elif game_board.piece_at(target) and game_board.piece_at(target).color == chess.WHITE:
                                    selected_square = target
                                    legal_targets = game_legal_targets(game_board, target)
                                else:
                                    selected_square, legal_targets = None, []
                            elif game_board.piece_at(target) and game_board.piece_at(target).color == chess.WHITE:
                                selected_square = target
                                legal_targets = game_legal_targets(game_board, target)
        while not worker.empty():
            status, payload = worker.get()
            if status == "progress":
                algorithm, visited, leaves, cutoffs, pruned, started = payload
                elapsed = max(0.0, (pygame.time.get_ticks() - started) / 1000)
                message = f"{algorithm} depth {search_depth}: {visited:,} visited nodes, {leaves:,} leaves, {elapsed:.1f}s"
            elif status == "ok":
                busy = False
                result = payload
                message = f"Completed at depth {result['depth']}. Scores match: {result['summary']['same_score']}."
            else:
                busy = False
                message = "Search error: " + payload
        while not engine_queue.empty():
            status, payload = engine_queue.get()
            engine_busy = False
            if status == "ok":
                if payload and payload[0]["move"] in game_board.legal_moves:
                    move = payload[0]["move"]
                    san = game_board.san(move)
                    game_board.push(move)
                    if game_board.is_game_over(claim_draw=True):
                        simulation_active = False
                        game_message = format_game_outcome(game_board)
                    elif simulation_active:
                        game_message = f"Simulation: {'White' if game_board.turn else 'Black'} to move…"
                        request_engine_move()
                    else:
                        game_message = f"Stockfish played {san}. Your move."
                else:
                    simulation_active = False
                    game_message = format_game_outcome(game_board)
            else:
                simulation_active = False
                game_message = f"Stockfish error: {payload}"
        while not minimax_queue.empty():
            status, payload = minimax_queue.get()
            if status == "progress":
                minimax_progress = payload
            elif status == "ok":
                if game_board.fen() != minimax_root_fen:
                    minimax_busy = False
                    minimax_candidates = []
                    game_message = "Minimax result discarded because the position changed."
                    continue
                minimax_result = payload
                root_moves = [node for node in payload.get("nodes", [])
                              if node.get("parent") == 0 and node.get("kind") == "move"]
                by_san = {node.get("san"): node for node in root_moves}
                minimax_candidates = [
                    {"san": move["san"], "score": by_san.get(move["san"], {}).get("score"), "move": move["move"]}
                    for move in minimax_candidates
                ]
                minimax_candidates.sort(key=lambda item: item.get("score") if item.get("score") is not None else -math.inf,
                                        reverse=True)
                minimax_apply_at = time.monotonic() + 2.0
                game_message = (f"Minimax reviewed {len(minimax_candidates)} legal moves and chose "
                                f"{payload['best_move_san']} ({format_search_score(payload['best_score'])}).")
            elif status in ("error", "cancelled"):
                minimax_busy = False
                minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                game_message = f"Minimax error: {payload}" if status == "error" else "Minimax search cancelled."
        while not match_queue.empty():
            status, payload = match_queue.get()
            if status == "move_preview":
                root_fen, match_preview_groups, preview_ack = payload
                match_preview_done_ack = preview_ack
                match_preview_index = 0
                match_boards = {key: chess.Board(root_fen) for key in ("minimax", "alpha_beta")}
                match_preview_active = bool(match_preview_groups)
                match_preview_next_at = time.monotonic() + MATCH_PREVIEW_INTERVAL
                if match_preview_active:
                    match_message = move_preview_message(match_preview_groups, match_preview_index)
                else:
                    preview_ack.set()
            elif status == "match_progress":
                key, visited, leaves, cutoffs, pruned, elapsed = payload
                if key in match_stats:
                    match_stats[key]["current"] = (visited, leaves, cutoffs, pruned, elapsed)
            elif status == "search_started":
                key, root_fen = payload
                match_active_algorithm = key
                match_searching_algorithms.add(key)
                match_boards[key] = chess.Board(root_fen)
                match_cursor_bounds[key] = (None, None)
                match_stats[key]["current"] = (0, 0, 0, 0, 0.0)
                match_stats[key]["turn_done"] = False
                match_message = ("Minimax and Alpha-Beta are exploring this same position concurrently."
                                 if len(match_searching_algorithms) == 2 else
                                 f"{key.replace('_', ' ').title()} is exploring the shared position…")
            elif status == "match_cursor":
                key, root_fen, path, ply, alpha, beta, visited, leaves, cutoffs, pruned, elapsed, acknowledgement = payload
                cursor_board = chess.Board(root_fen)
                for uci in path:
                    cursor_board.push_uci(uci)
                match_boards[key] = cursor_board
                match_active_algorithm = key
                match_searching_algorithms.add(key)
                match_cursor_bounds[key] = (alpha, beta)
                match_stats[key]["current"] = (visited, leaves, cutoffs, pruned, elapsed)
                match_pending_acks.append(acknowledgement)
                match_ack_release_at = max(match_ack_release_at, time.perf_counter() + MATCH_ACK_INTERVAL)
            elif status == "search_done":
                key, best_uci, best_san, item = payload
                stats = match_stats[key]
                stats["nodes_visited"] += item["nodes_visited"]
                stats["leaf_nodes_evaluated"] += item["leaf_nodes_evaluated"]
                stats["cutoffs"] += item["cutoffs"]
                stats["pruned_moves"] += item["pruned_moves"]
                stats["elapsed"] += item["elapsed"]
                stats["wall_time"] += item["wall_time"]
                stats["searches"] = stats.get("searches", 0) + 1
                stats["last_move"], stats["last_score"] = best_san, item["best_score"]
                stats["last_search_wall_time"] = item["wall_time"]
                stats["last_search_pruned"] = item["pruned_moves"]
                stats["turn_done"] = True
                stats["current"] = (0, 0, 0, 0, 0.0)
                match_searching_algorithms.discard(key)
                match_message = f"{key.replace('_', ' ').title()} finished searching: {best_san}."
                if all(match_stats[algo].get("turn_done") for algo in ("minimax", "alpha_beta")):
                    minimax_time = match_stats["minimax"]["last_search_wall_time"]
                    alpha_beta_time = match_stats["alpha_beta"]["last_search_wall_time"]
                    if minimax_time > alpha_beta_time and minimax_time > 0:
                        advantage = (minimax_time - alpha_beta_time) / minimax_time * 100
                        match_message = (f"Both searches chose {best_san}. Alpha-Beta finished {advantage:.0f}% sooner "
                                         f"({alpha_beta_time:.2f}s vs Minimax {minimax_time:.2f}s); "
                                         f"it pruned {match_stats['alpha_beta']['last_search_pruned']:,} move(s) this search.")
                    else:
                        match_message = (f"Both depth-{MATCH_DEPTH} searches finished: Minimax {minimax_time:.2f}s, "
                                         f"Alpha-Beta {alpha_beta_time:.2f}s. See the per-search pruning counts in each panel.")
            elif status == "game_move":
                uci, san, fen, ply = payload
                move = chess.Move.from_uci(uci)
                if move in match_game_board.legal_moves:
                    match_game_board.push(move)
                match_boards = {key: match_game_board.copy(stack=True) for key in ("minimax", "alpha_beta")}
                match_active_algorithm = None
                match_searching_algorithms.clear()
                match_message = f"Both searches completed. {san} advances the shared game; they now search the next position."
            elif status == "match_done":
                match_running = False
                match_preview_active = False
                outcome, termination = payload
                match_boards = {key: match_game_board.copy(stack=True) for key in ("minimax", "alpha_beta")}
                match_active_algorithm = None
                match_searching_algorithms.clear()
                minimax_time = match_stats["minimax"].get("last_search_wall_time", 0.0)
                alpha_beta_time = match_stats["alpha_beta"].get("last_search_wall_time", 0.0)
                if minimax_time > alpha_beta_time and minimax_time > 0:
                    advantage = (minimax_time - alpha_beta_time) / minimax_time * 100
                    faster = (f" Alpha-Beta finished {advantage:.0f}% sooner ({alpha_beta_time:.2f}s vs "
                              f"Minimax {minimax_time:.2f}s) and pruned "
                              f"{match_stats['alpha_beta'].get('last_search_pruned', 0):,} moves.")
                elif minimax_time or alpha_beta_time:
                    faster = (f" Search times: Minimax {minimax_time:.2f}s, Alpha-Beta {alpha_beta_time:.2f}s; "
                              "compare the numeric node and pruning totals in the two panels.")
                else:
                    faster = ""
                match_message = (f"Game ended {outcome} ({termination.replace('_', ' ').lower()})."
                                 f" Both searches reached the result.{faster} Totals are final.")
            elif status == "match_cancelled":
                match_running = False
                match_preview_active = False
                match_active_algorithm = None
                match_searching_algorithms.clear()
                match_message = "Games stopped. Partial games and accumulated statistics are retained."
            elif status == "match_error":
                match_running = False
                match_preview_active = False
                match_active_algorithm = None
                match_message = f"Game search error: {payload}"
        if match_preview_active and time.monotonic() >= match_preview_next_at:
            match_preview_index += 1
            if match_preview_index >= len(match_preview_groups):
                match_preview_active = False
                if match_preview_done_ack:
                    match_preview_done_ack.set()
                    match_preview_done_ack = None
                match_message = "Legal moves shown. Minimax and Alpha-Beta are starting their searches."
            else:
                match_preview_next_at = time.monotonic() + MATCH_PREVIEW_INTERVAL
                match_message = move_preview_message(match_preview_groups, match_preview_index)
        draw()
        pygame.display.flip()
        clock.tick(60)
        if minimax_busy and minimax_result and minimax_apply_at and time.monotonic() >= minimax_apply_at:
            if game_board.fen() == minimax_root_fen:
                move = chess.Move.from_uci(minimax_result["best_move"])
                if move in game_board.legal_moves:
                    san = game_board.san(move)
                    game_board.push(move)
                    minimax_busy = False
                    minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
                    selected_square, legal_targets = None, []
                    if game_board.is_game_over(claim_draw=True):
                        game_message = format_game_outcome(game_board)
                    else:
                        request_engine_move()
                else:
                    minimax_busy = False
                    game_message = "Minimax chose a move that is no longer legal."
            else:
                minimax_busy = False
                minimax_result, minimax_candidates, minimax_apply_at = None, [], 0.0
        if match_pending_acks and time.perf_counter() >= match_ack_release_at:
            pending, match_pending_acks = match_pending_acks, []
            match_ack_release_at = 0.0
            for acknowledgement in pending:
                acknowledgement.set()
    if match_running:
        stop_parallel_games()
    for acknowledgement in match_pending_acks:
        acknowledgement.set()
    match_pending_acks.clear()
    if match_thread and match_thread.is_alive():
        match_thread.join()
    if match_preview_done_ack:
        match_preview_done_ack.set()
    if minimax_cancel:
        minimax_cancel.set()
    if minimax_thread and minimax_thread.is_alive():
        minimax_thread.join()
    if engine_thread and engine_thread.is_alive():
        engine_thread.join()
    pygame.quit()


if __name__ == "__main__":
    main()
