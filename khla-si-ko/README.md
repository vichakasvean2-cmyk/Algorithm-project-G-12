# Kla Si Ko

A two-player board game on a 4×4 checkerboard with a fixed 12-cow match. Pieces move between adjacent squares along rows and columns.

## Run the game

On Windows, double-click `run_game.bat`. On first launch, it creates the project virtual environment and installs the required packages; this may take a few minutes. You need Python installed and an internet connection for this first setup.

Alternatively, run these commands from the project folder:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## How to play

- Smile and hold briefly in view of the webcam to start a game. You can also click **Start Challenge** or press `Space`/`Enter`.
- The four tigers start on the board's four corner squares.
- The cow player goes first and places 12 cows, one per turn, on empty squares.
- After each cow placement, the tiger player selects a tiger and then an adjacent empty square.
- Tigers move horizontally or vertically. A tiger may capture a cow by jumping over it into the empty square beyond.
- Once all 12 cows are placed, cows move one square horizontally or vertically to an empty square on their turns.
- Cows win by trapping all four tigers so they have no legal move.
- Tigers win by capturing all 12 cows, or by trapping all cows so none can move.
- A draw occurs if the same board position, turn, and cow counts occur three times.

The webcam opens automatically at 640×480. On first use, the game may download the MediaPipe face model needed for smile-to-start. Hold a clear smile toward the camera briefly to start. During the game, use your left hand to select and move tigers, and your right hand to place or move cows. Point at a glowing board square and pinch to click. For a tiger move, pinch once on a tiger and again on a green highlighted destination. Pinch the selected tiger again to cancel. Camera pointing and pinching can also select buttons throughout the home screen, settings, and result screen. Mouse clicks work as a backup and can make moves for either side. Press `R` to restart the game, `Esc`/`H` to return home, or `Q` to quit.

Open **Settings** from the home screen or game screen, or press `S`, to enable/disable audio, the three-second countdown sound, and gesture confirmation sounds independently. Round endings play distinct win, lose, or draw sounds and show a brief pulsing result animation. Audio settings apply for the current run of the game.

## Tests

```powershell
python -m pytest -q
```
