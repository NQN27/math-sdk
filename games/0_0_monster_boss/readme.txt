# Monster Cluster Boss Battle

5x5 cluster-pays game. Clusters of 5 or more like-symbols (wild substitutes) are removed from
the board, and symbols above on the reelstrip fall to fill their place.

#### Basegame:
Standard tumbling game with Scatter and Wild symbols.
3 Scatter symbols trigger Normal Free Spins; 4+ Scatter symbols trigger VIP Free Spins (drawn
from a more generous reel set with more wilds/high symbols and fewer low-pay symbols).

3 bosses are shown above the board, each "owning" a column zone (Boss1: reels 0-2, Boss2: reels
1-3, Boss3: reels 3-4). Every winning cluster damages whichever boss(es) it overlaps, by the
cluster's paid win amount; a cluster spanning all 5 reels deals bonus damage (2x) to every boss
it touches. Boss HP resets at the start of every new base-game spin sequence. Defeating all 3
bosses in one sequence awards an instant bonus win (base-game win, not a free-spin trigger -
see the note below on why).

#### Freegame:
Same basegame rule, except grid positions have multipliers. Grid positions start in a
'deactivated' state. Once one win occurs, the position is 'activated' starting with a 1x
multiplier - for every winning cluster, the multiplier value at that position is increased by
+1 for every winning position. A minimum of 3 scatters are required for re-triggers.

The boss battle mechanic does not run during free spins (base-game only).

#### Notes:
Because of the separation between basegame and freegame types - there is an additional freespin
entry check to check if the criteria requires a forced freespin condition. Otherwise, occurences
of Scatter symbols tumbling onto the board during basegame criteria may appear.

The boss-defeat bonus is deliberately an instant base-game win rather than a free-spin trigger.
This engine's analytics tooling (utils/game_analytics/get_pay_splits.py) attributes each
simulation's optimizer "fence" purely by which Distribution criteria generated it (see
write_data.make_lookup_pay_split). Boss-defeat is an unforced event that can occur during an
ordinary 'basegame'-criteria spin, and there's no way to force it onto a board the way scatter
counts can be forced - so a nonzero *free-game* win recorded under 'basegame' criteria has no
dedicated fence to be reassigned to, and hard-fails that tooling's "Non-Zero FreeGame win in
baseGame Fence" check once enough simulations are run for the rare event to occur (observed at
100k sims/mode; did not surface at 2k). Keeping the reward as a base-game win avoids this
structural conflict entirely.
