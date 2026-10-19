import unittest

from src.tiger_cows_game import COW, TIGER, TigerCowsGame


class TigerCowsGameTests(unittest.TestCase):
    def test_game_starts_with_tigers_in_corners_and_cows_to_place(self):
        game = TigerCowsGame()

        self.assertEqual([index for index, piece in enumerate(game.board) if piece == TIGER], [0, 3, 12, 15])
        self.assertEqual(game.turn, "cows")
        self.assertEqual(game.cows_remaining, 9)

    def test_difficulty_levels_set_cow_count_and_restart_the_game(self):
        game = TigerCowsGame()
        game.click_node(5)

        game.set_level("Beginner")

        self.assertEqual(game.level, "Beginner")
        self.assertEqual(game.cows_remaining, 6)
        self.assertEqual(game.cows_placed, 0)
        self.assertEqual(game.turn, "cows")
        self.assertEqual([index for index, piece in enumerate(game.board) if piece == TIGER], [0, 3, 12, 15])

        game.set_level("Normal")
        self.assertEqual(game.cows_remaining, 9)
        game.set_level("Hard")
        self.assertEqual(game.cows_remaining, 12)

    def test_unknown_difficulty_level_is_rejected(self):
        game = TigerCowsGame()

        with self.assertRaises(ValueError):
            game.set_level("Expert")

    def test_same_position_three_times_results_in_a_draw(self):
        game = TigerCowsGame()

        game._record_position()
        self.assertFalse(game.game_over)
        game._record_position()

        self.assertEqual(game.winner, "Draw")
        self.assertEqual(game.status, "Draw! The same board position occurred three times.")
        self.assertIsNone(game.selected_node)

    def test_cows_place_then_tigers_move(self):
        game = TigerCowsGame()

        self.assertTrue(game.click_node(5))
        self.assertEqual(game.board[5], COW)
        self.assertEqual(game.cows_placed, 1)
        self.assertEqual(game.turn, "tigers")
        self.assertTrue(game.click_node(0))
        self.assertTrue(game.click_node(1))
        self.assertEqual(game.board[0], None)
        self.assertEqual(game.board[1], TIGER)
        self.assertEqual(game.turn, "cows")
        self.assertEqual(game.last_move, (0, 1, TIGER))
        self.assertEqual(game.move_count, 1)

    def test_clicking_selected_piece_cancels_selection(self):
        game = TigerCowsGame()
        game.click_node(5)
        game.click_node(0)
        self.assertEqual(game.selected_node, 0)

        self.assertTrue(game.click_node(0))

        self.assertIsNone(game.selected_node)
        self.assertIn("canceled", game.status.lower())

    def test_clicking_another_friendly_piece_changes_selection(self):
        game = TigerCowsGame()
        game.click_node(5)
        game.click_node(0)

        self.assertTrue(game.click_node(3))

        self.assertEqual(game.selected_node, 3)

    def test_tiger_jumps_over_and_captures_cow(self):
        game = TigerCowsGame()

        game.click_node(1)
        self.assertTrue(game.click_node(0))
        self.assertIn(2, game.legal_targets(0))
        self.assertTrue(game.click_node(2))

        self.assertEqual(game.board[1], None)
        self.assertEqual(game.board[2], TIGER)
        self.assertEqual(game.cows_captured, 1)
        self.assertEqual(game.turn, "cows")

    def test_cows_can_move_after_all_twelve_have_been_placed(self):
        game = TigerCowsGame()
        game.cows_placed = 12
        game.turn = "cows"
        game.board[5] = COW

        self.assertTrue(game.click_node(5))
        self.assertTrue(game.click_node(6))
        self.assertEqual(game.board[5], None)
        self.assertEqual(game.board[6], COW)
        self.assertEqual(game.turn, "tigers")

    def test_cows_win_when_their_last_placement_traps_every_tiger(self):
        game = TigerCowsGame()
        game.set_level("Hard")
        game.cows_placed = 11
        game.board = [
            TIGER, None, COW, TIGER,
            COW, COW, COW, COW,
            COW, COW, COW, COW,
            TIGER, COW, COW, TIGER,
        ]

        self.assertTrue(game.click_node(1))
        self.assertEqual(game.winner, "Cows")
        self.assertTrue(game.game_over)

    def test_tigers_win_after_capturing_the_twelfth_cow(self):
        game = TigerCowsGame()
        game.set_level("Hard")
        game.turn = "tigers"
        game.cows_placed = 12
        game.cows_captured = 11
        game.board[0] = TIGER
        game.board[1] = COW
        game.board[2] = None

        game.click_node(0)
        self.assertTrue(game.click_node(2))
        self.assertEqual(game.winner, "Tigers")
        self.assertEqual(game.cows_captured, 12)

    def test_tigers_win_after_capturing_all_cows_for_the_selected_level(self):
        game = TigerCowsGame()
        game.set_level("Beginner")
        game.turn = "tigers"
        game.cows_placed = 6
        game.cows_captured = 5
        game.board[0] = TIGER
        game.board[1] = COW
        game.board[2] = None

        game.click_node(0)
        self.assertTrue(game.click_node(2))

        self.assertEqual(game.winner, "Tigers")
        self.assertEqual(game.cows_captured, 6)

    def test_reset_restores_initial_board(self):
        game = TigerCowsGame()
        game.click_node(5)

        game.reset()

        self.assertEqual([index for index, piece in enumerate(game.board) if piece == TIGER], [0, 3, 12, 15])
        self.assertEqual(game.cows_remaining, 9)
        self.assertEqual(game.turn, "cows")
        self.assertFalse(game.game_over)
        self.assertIsNone(game.last_move)


if __name__ == "__main__":
    unittest.main()
