# Game Data Tables

Place `.xlsx` game data tables in subdirectories by module name.

Example structure:

```
gamedata/
  Scene/
    Scene.xlsx
    SceneArea.xlsx
  HomeLand/
    HomeBuildingType.xlsx
    HomeHero.xlsx
```

After running `python references/scripts/core/table_reader.py`, knowledge md files will be generated in `knowledge/`.

Source files (.xlsx) are not tracked by git.
