# S-Type (Gradius Clone)

*This is a project coded almost entirely by Antigravity, to see how capable it is at taking human-readable chat prompts and translating them into actionable code.*

**S-Type** is a high-fidelity recreation of the classic *Gradius III* mechanics, built with Python and Pygame CE. It aims to capture the precise feel of the Vic Viper's movement, weapon systems, and power-up mechanics.

## 🎮 Current Release: Alpha 0.2
> **Status**: Playable Prototype (Invulnerability, Options, Shields, Weapon System)

### Features
-   **Native HD Resolution**: 768x672 (3x Scale of original SNES 256x224).
-   **Vic Viper**: Authentic movement physics, banking animations, and speed-up cycles.
-   **Weapon System**:
    -   **Speed Up**: Cyclical speed increase (up to 5 levels).
    -   **Missile**: Ground-hugging missiles that traverse terrain.
    -   **Double**: Tailgun / Vertical fire.
    -   **Laser**: Piercing blue laser.
    -   **Option**: Up to 4 ghost ships that follow your exact movement path.
    -   **Shield**: Frontal barrier (5 HP) that visually degrades.
    -   **(!)**: Mega Crush / Shield Recharge.
-   **Enemies**: Basic enemy waves and collision logic.

## ⌨️ Controls
| Action | Key | Description |
| :--- | :---: | :--- |
| **Move** | `Arrow Keys` | Pilot the Vic Viper |
| **Shoot** | `Z` | Fire Primary Weapon |
| **Missile** | `X` | Fire Missiles (if equipped) |
| **Both** | `S` | Fire Both weapons simultaneously |
| **Power Up** | `A` | Activate highlighted Power-Up |
| **Debug Spawn** | `C` | Spawn a Red Capsule (Testing) |
| **Quit** | `ESC` | Exit Game |

## 🛠️ Installation & Development

### Equivalents
-   Python 3.10+
-   Pygame CE (`pip install pygame-ce`)

### Running form Source
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the game:
    ```bash
    python main.py
    ```

### Building Executable
To build a standalone `.exe`:
```bash
pip install pyinstaller
pyinstaller --name "S-Type_Alpha_0.2" --noconfirm --onefile --windowed --add-data "assets;assets" main.py
```
The output file will be in the `dist/` folder.

##  Credits
-   **Engine**: Custom Pygame loop using ECS pattern.
-   **Sprites**: The Spriters Resource (Gradius III / Gradius Gaiden).
-   **Inspiration**: Konami's Gradius Series.
