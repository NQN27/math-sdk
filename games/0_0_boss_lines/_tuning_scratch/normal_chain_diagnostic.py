import sys, random, warnings, statistics
sys.path.insert(0, r"D:\Stake Engine\math-sdk")
sys.path.insert(0, r"D:\Stake Engine\math-sdk\games\0_0_boss_lines")
import gamestate as gamestate_mod
import game_config as game_config_mod
from src.wins.win_manager import WinManager

# Instrument (test-only monkeypatch, no production code touched): count how
# many times evaluate_and_explode fires per internal Bonus spin. The FIRST
# call is always the initial reveal (fires unconditionally); every call
# after that is one more tumble/cascade in the SAME spin's chain. So
# pass_count==1 for a spin means "initial reveal had zero winning lines -
# no cascade/tumble ever happened that spin", pass_count==2 means one
# cascade happened, etc. This directly answers "is a short/zero win-chain
# on spin 1 what's causing instant death?"
_original_evaluate = gamestate_mod.GameState.evaluate_and_explode
_original_run_one_bonus_spin = gamestate_mod.GameState.run_one_bonus_spin


def _patched_evaluate(self, *a, **kw):
    self._diag_pass_count = getattr(self, "_diag_pass_count", 0) + 1
    return _original_evaluate(self, *a, **kw)


def _patched_run_one_bonus_spin(self, both_ways):
    self._diag_pass_count = 0
    result = _original_run_one_bonus_spin(self, both_ways)
    if not hasattr(self, "_diag_spin_chain_lengths"):
        self._diag_spin_chain_lengths = []
    self._diag_spin_chain_lengths.append(self._diag_pass_count)
    return result


gamestate_mod.GameState.evaluate_and_explode = _patched_evaluate
gamestate_mod.GameState.run_one_bonus_spin = _patched_run_one_bonus_spin

config = game_config_mod.GameConfig()
config.bonus_safety_cap_spins = 150
gs = gamestate_mod.GameState(config)
gs.win_manager = WinManager(config.basegame_type, config.freegame_type, config.wincap)
gs.betmode = "base"

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000

spin1_chain = []          # chain length of this session's FIRST internal spin
spin1_chain_by_outcome = {"zero_payout": [], "under5x": [], "over5x": []}
all_chain_lengths = []    # chain length of EVERY internal spin, all sessions
died_spin1_chain0 = 0     # sessions that died on spin1 with chain==1 (no win at all that spin)
died_spin1_total = 0

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for i in range(n):
        gs.sim = i
        gs.criteria = "freegame"
        random.seed(271828 * 1000003 + i + 1)
        gs.reset_book()
        gs._diag_spin_chain_lengths = []
        gs.run_bonus_session("normal")
        payout = gs.win_manager.running_bet_win
        spins_survived = getattr(gs, "bonus_spin_count", None)
        chains = gs._diag_spin_chain_lengths
        all_chain_lengths.extend(chains)
        if chains:
            spin1_chain.append(chains[0])
            if payout == 0:
                spin1_chain_by_outcome["zero_payout"].append(chains[0])
            elif payout < 5:
                spin1_chain_by_outcome["under5x"].append(chains[0])
            else:
                spin1_chain_by_outcome["over5x"].append(chains[0])
        if spins_survived == 1:
            died_spin1_total += 1
            if chains and chains[0] == 1:
                died_spin1_chain0 += 1

print(f"=== n={n} sessions ===")
print(f"Spin-1 chain length (1 = initial reveal had NO win, no cascade at all that spin):")
dist = {v: spin1_chain.count(v) for v in sorted(set(spin1_chain))}
print(f"  full distribution: {dist}")
print(f"  mean={statistics.mean(spin1_chain):.2f} median={statistics.median(spin1_chain)}")
print()
for label, group in spin1_chain_by_outcome.items():
    if not group:
        print(f"{label}: n=0")
        continue
    chain0_pct = 100 * sum(1 for c in group if c == 1) / len(group)
    print(f"{label}: n={len(group)}, spin1-chain==1 (dead reveal) rate = {chain0_pct:.1f}%, "
          f"mean chain = {statistics.mean(group):.2f}")
print()
print(f"Sessions that died on spin 1: {died_spin1_total} ({100*died_spin1_total/n:.2f}% of all)")
print(f"  ...of which spin-1 chain was exactly 1 (totally dead reveal, 0 wins/cascades): "
      f"{died_spin1_chain0} ({100*died_spin1_chain0/died_spin1_total:.1f}% of spin-1 deaths)" if died_spin1_total else "n/a")
print()
print(f"ALL internal spins (every spin, every session) chain-length distribution:")
all_dist = {v: all_chain_lengths.count(v) for v in sorted(set(all_chain_lengths))}
print(f"  {all_dist}")
print(f"  mean chain length overall = {statistics.mean(all_chain_lengths):.2f}, "
      f"% of ALL spins with chain==1 (no win at all) = "
      f"{100*sum(1 for c in all_chain_lengths if c==1)/len(all_chain_lengths):.1f}%")
