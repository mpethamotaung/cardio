import pytest
from cardio import Card, FightCard, GridPos
from cardio import skills as sk
from cardio.deck import FightDecks


@pytest.fixture
def common_setup(mocker, tt_setup):
    human, grid, *_ = tt_setup
    mocked_vnc = mocker.Mock()
    mocked_vnc.decks = FightDecks()
    mocked_vnc.humanplayer = human
    FightCard.init_fight(mocked_vnc, grid)
    c = Card("X", 1, 2, 3)
    fc = FightCard.from_card(c)
    grid[2][3] = fc
    grid[1][3] = fc.copy()
    grid[0][3] = fc.copy()
    yield c, fc, grid, mocked_vnc


def test_from_to_card(common_setup):
    c, fc, *_ = common_setup
    assert isinstance(fc, FightCard)
    assert fc.to_card() is c
    assert fc.name == "X"
    assert fc.power == 1
    assert fc.health == 2
    assert fc.costs_fire == 3


def test_fightcard_leaves_original_untouched(common_setup):
    c, fc, *_ = common_setup
    fc.name = "New"
    fc.power = 10
    fc.health = 0
    x = fc.to_card()
    del fc
    assert x is c
    assert x.name == "X"
    assert x.power == 1
    assert x.health == 2
    assert x.costs_fire == 3


def test_fightcard_simple_method_access(common_setup):
    _, fc, *_ = common_setup
    assert not fc.is_skilled()


def test_is_human(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    assert fc.is_human()  # common_setup puts fc on the grid
    grid[2][3] = None
    assert not fc.is_human()
    mocked_vnc.decks.draw.add_card(fc)
    assert fc.is_human()
    mocked_vnc.decks = FightDecks()
    assert not fc.is_human()


def test_copy(common_setup):
    c, fc, *_ = common_setup
    fc2 = fc.copy()
    assert fc2 is not fc
    assert isinstance(fc2, FightCard)
    assert fc2.name == "X"
    assert fc2.vnc is fc.vnc
    assert fc2.grid is fc.grid
    assert fc2.to_card() is c


def test_get_grid_pos(common_setup):
    _, fc, *_ = common_setup
    assert fc.get_grid_pos() == GridPos(2, 3)


def test_get_prep_card(common_setup):
    _, fc, grid, _ = common_setup
    assert fc.get_prep_card() == grid[0][3]


def test_die(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    spirits_before = mocked_vnc.humanplayer.spirits
    assert fc.health == 2
    fc.die()
    assert fc.health == 0
    assert mocked_vnc.humanplayer.spirits == spirits_before + 1
    mocked_vnc.card_died.assert_called_once()
    assert grid[2][3] is None


def test_no_spirits_when_computer_card_dies(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    spirits_before = mocked_vnc.humanplayer.spirits
    grid[1][3], grid[2][3] = fc, grid[1][3]  # Swap cards
    assert fc.health == 2
    fc.die()
    assert fc.health == 0
    assert mocked_vnc.humanplayer.spirits == spirits_before
    mocked_vnc.card_died.assert_called_once()
    assert grid[1][3] is None


def test_sacrifice(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    spirits_before = mocked_vnc.humanplayer.spirits
    assert fc.health == 2
    has_fire = fc.sacrifice()
    assert has_fire == 1
    assert fc.health == 0
    assert (
        mocked_vnc.humanplayer.spirits == spirits_before
    )  # sacrificing must not give spirits
    mocked_vnc.card_died.assert_not_called()
    assert grid[2][3] is None


def test_take_damage(common_setup):
    _, fc, _, mocked_vnc = common_setup
    fc.health = 10
    damage_left = fc.take_damage(3)
    assert damage_left == 0
    assert fc.health == 7
    mocked_vnc.card_lost_health.assert_called_once()
    mocked_vnc.card_died.assert_not_called()


def test_take_damage_calculates_damage_left_correctly(common_setup):
    _, fc, grid, _ = common_setup
    # With shield:
    fc.health = 1
    fc2 = fc.copy()
    fc.skills.add(sk.Shield)
    damage_left = fc.take_damage(2)
    assert damage_left == 0  # Shield and card absorbed all damage
    # Without shield:
    grid[2][3] = fc2
    damage_left = fc2.take_damage(2)
    assert damage_left == 1  # The card only absorbed 1 of 2 damage


def test_take_damage_and_die(common_setup):
    _, fc, _, mocked_vnc = common_setup
    damage_left = fc.take_damage(100)
    assert damage_left == 98
    assert fc.health == 0
    mocked_vnc.card_died.assert_called_once()


def test_heal_damage(common_setup):
    _, fc, *_ = common_setup
    fc.health = 1
    fc.heal_damage(1)
    assert fc.health == 2
    fc.heal_damage(1)
    assert fc.health == 2  # Cannot heal above max health


def test_prepare_moves_card_from_prepline_to_computer_line(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    prep_card = grid[0][3]
    assert prep_card is not None
    grid[1][3] = None  # Clear computer line slot
    result = prep_card.prepare()
    assert result is True
    assert grid[0][3] is None
    assert grid[1][3] is prep_card
    mocked_vnc.show_card_prepare.assert_called_once_with(prep_card)


def test_prepare_fails_when_computer_line_occupied(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    prep_card = grid[0][3]
    assert prep_card is not None
    assert grid[1][3] is not None  # Computer line occupied
    result = prep_card.prepare()
    assert result is False
    assert grid[0][3] is prep_card
    mocked_vnc.show_card_prepare.assert_not_called()


def test_attack_with_zero_power_does_nothing(common_setup):
    _, fc, _, mocked_vnc = common_setup
    fc.power = 0
    fc.attack(target=None)
    mocked_vnc.show_card_activate.assert_not_called()
    mocked_vnc.handle_agent_damage.assert_not_called()


def test_attack_against_agent_directly(common_setup):
    _, fc, _, mocked_vnc = common_setup
    fc.power = 3
    fc.attack(target=None)
    mocked_vnc.show_card_activate.assert_called_once_with(fc)
    mocked_vnc.handle_agent_damage.assert_called_once_with("computer", 3)


def test_attack_against_opposing_card(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    fc.power = 2
    target = grid[1][3]
    target.health = 5
    fc.attack(target=target)
    mocked_vnc.show_card_activate.assert_called_once_with(fc)
    mocked_vnc.show_card_getting_attacked.assert_called_once_with(target, fc)
    assert target.health == 3


def test_attack_kills_target(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    fc.power = 10
    target = grid[1][3]
    target.health = 2
    fc.attack(target=target)
    assert target.health == 0
    mocked_vnc.card_died.assert_called_once()


def test_attack_overflow_damage_to_agent(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    fc.power = 10
    target = grid[1][3]
    target.health = 3
    fc.attack(target=target)
    mocked_vnc.handle_agent_damage.assert_called_once_with("computer", 7)


def test_attack_with_underdog_gains_power(common_setup):
    _, fc, grid, _ = common_setup
    fc.power = 2
    fc.skills.add(sk.Underdog)
    target = grid[1][3]
    target.power = 5
    target.health = 10
    fc.attack(target=target)
    assert target.health == 7  # 2 + 1 (Underdog) = 3 damage


def test_attack_with_weakness_reduces_damage(common_setup):
    _, fc, grid, _ = common_setup
    fc.power = 3
    fc.skills.add(sk.Weakness)
    target = grid[1][3]
    target.health = 10
    fc.attack(target=target)
    assert target.health == 8  # 3 - 1 (Weakness) = 2 damage


def test_attack_with_weakness_minimum_zero_damage(common_setup):
    _, fc, _, mocked_vnc = common_setup
    fc.power = 1
    fc.skills.add(sk.Weakness)
    fc.attack(target=None)
    mocked_vnc.show_card_activate.assert_called_once()
    mocked_vnc.handle_agent_damage.assert_called_once_with("computer", 0)


def test_attack_with_soaring_bypasses_target(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    fc.power = 3
    fc.skills.add(sk.Soaring)
    target = grid[1][3]
    target.health = 10
    fc.attack(target=target)
    mocked_vnc.handle_agent_damage.assert_called_once_with("computer", 3)
    assert target.health == 10


def test_attack_with_soaring_blocked_by_airdefense(common_setup):
    _, fc, grid, _ = common_setup
    fc.power = 3
    fc.skills.add(sk.Soaring)
    target = grid[1][3]
    target.health = 10
    target.skills.add(sk.Airdefense)
    fc.attack(target=target)
    assert target.health == 7


def test_attack_with_instant_death_kills_target(common_setup):
    _, fc, grid, mocked_vnc = common_setup
    fc.power = 1
    fc.skills.add(sk.InstantDeath)
    target = grid[1][3]
    target.health = 100
    fc.attack(target=target)
    assert target.health == 0
    mocked_vnc.card_died.assert_called_once()


def test_attack_against_target_with_spines(common_setup):
    _, fc, grid, _ = common_setup
    fc.power = 2
    fc.health = 5
    target = grid[1][3]
    target.health = 10
    target.skills.add(sk.Spines)
    fc.attack(target=target)
    assert target.health == 8
    assert fc.health == 4


def test_attack_computer_card_attacks_human_agent(common_setup):
    _, _, grid, mocked_vnc = common_setup
    grid[2][3] = None
    computer_card = grid[1][3]
    computer_card.power = 4
    computer_card.attack(target=None)
    mocked_vnc.handle_agent_damage.assert_called_once_with("human", 4)
