# Tigers and Cows

A two-player board game on a 4×4 checkerboard. Pieces move between adjacent squares along rows and columns.

## Run the game

On Windows, double-click `run_game.bat`. On first launch, it creates the project virtual environment and installs the required packages; this may take a few minutes. You need Python installed and an internet connection for this first setup.

Alternatively, run these commands from the project folder:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## How to play

- The home screen lets you choose Beginner, Normal, or Hard. Smile and hold briefly in view of the webcam to start the selected level. You can also click **Start Challenge** or press `Space`/`Enter`.
- The four tigers start on the board's four corner squares.
- Choose Beginner (6 cows), Normal (9 cows), or Hard (12 cows) using the buttons beside the board, or keys `1`, `2`, and `3`. Selecting a level starts a new game.
- The cow player goes first and places the number of cows for the selected level, one per turn, on empty squares.
- After each cow placement, the tiger player selects a tiger and then an adjacent empty square.
- Tigers move horizontally or vertically. A tiger may capture a cow by jumping over it into the empty square beyond.
- Once all cows for the selected level are placed, cows move one square horizontally or vertically to an empty square on their turns.
- Cows win by trapping all four tigers so they have no legal move.
- Tigers win by capturing all cows for the selected level, or by trapping all cows so none can move.
- A draw occurs if the same board position, turn, and cow counts occur three times.

The webcam opens automatically at 640×480. On first use, the game may download the MediaPipe face model needed for smile-to-start. Hold a clear smile toward the camera briefly to start the selected level. Camera pointing and pinching can also select buttons throughout the home screen, game, settings, and result screen. The tracker detects both hands, and either hand can point and pinch to click; each hand has its own cursor. During the game, point at a glowing board square and pinch to click. For a tiger move, pinch once on a tiger and again on a green highlighted destination. Pinch the selected tiger again to cancel. The game is turn-based, so players still take turns; each player can use either hand when it is their turn. Mouse clicks also work as a backup. Press `R` to restart the current level, `Esc`/`H` to return home, or `Q` to quit.

Open **Settings** from the home screen or game screen, or press `S`, to enable/disable audio, the three-second countdown sound, and gesture confirmation sounds independently. Either side winning plays applause; a draw has its own sound. Results also show a brief pulsing animation. Audio settings apply for the current run of the game.

## Tests

```powershell
python -m pytest -q
```
