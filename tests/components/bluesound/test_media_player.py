"""Tests for the Bluesound Media Player platform."""

import dataclasses
from unittest.mock import call

from pyblu import PairedPlayer
from pyblu.errors import PlayerUnreachableError
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.components.bluesound import DOMAIN as BLUESOUND_DOMAIN
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .conftest import PlayerMocks


async def test_pause(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player pause."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.pause.assert_called_once()


async def test_play(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player play."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PLAY,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.play.assert_called_once()


async def test_next_track(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player next track."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.skip.assert_called_once()


async def test_previous_track(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player previous track."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PREVIOUS_TRACK,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.back.assert_called_once()


async def test_volume_set(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player volume set."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: "media_player.player_name1111", "volume_level": 0.5},
        blocking=True,
    )

    player_mocks.player_data.player.volume.assert_called_once_with(level=50)


async def test_volume_mute(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player volume mute."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {ATTR_ENTITY_ID: "media_player.player_name1111", "is_volume_muted": True},
        blocking=True,
    )

    player_mocks.player_data.player.volume.assert_called_once_with(mute=True)


async def test_volume_up(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player volume up."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.volume.assert_called_once_with(level=11)


async def test_volume_down(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the media player volume down."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_DOWN,
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.volume.assert_called_once_with(level=9)


async def test_attributes_set(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks, snapshot: SnapshotAssertion
) -> None:
    """Test the media player attributes set."""
    state = hass.states.get("media_player.player_name1111")
    assert state == snapshot(exclude=props("media_position_updated_at"))


async def test_status_updated(
    hass: HomeAssistant,
    setup_config_entry: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test the media player status updated."""
    pre_state = hass.states.get("media_player.player_name1111")
    assert pre_state.state == "playing"
    assert pre_state.attributes["volume_level"] == 0.1

    status = player_mocks.player_data.status_long_polling_mock.get()
    status = dataclasses.replace(status, state="pause", volume=50, etag="changed")
    player_mocks.player_data.status_long_polling_mock.set(status)

    # give the long polling loop a chance to update the state; this could be any async call
    await hass.async_block_till_done()

    post_state = hass.states.get("media_player.player_name1111")

    assert post_state.state == MediaPlayerState.PAUSED
    assert post_state.attributes["volume_level"] == 0.5


async def test_unavailable_when_offline(
    hass: HomeAssistant,
    setup_config_entry: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test that the media player goes unavailable when the player is unreachable."""
    pre_state = hass.states.get("media_player.player_name1111")
    assert pre_state.state == "playing"

    player_mocks.player_data.status_long_polling_mock.set_error(
        PlayerUnreachableError("Player not reachable")
    )
    player_mocks.player_data.status_long_polling_mock.trigger()

    # give the long polling loop a chance to update the state; this could be any async call
    await hass.async_block_till_done()

    post_state = hass.states.get("media_player.player_name1111")

    assert post_state.state == "unavailable"


async def test_set_sleep_timer(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the set sleep timer action."""
    await hass.services.async_call(
        BLUESOUND_DOMAIN,
        "set_sleep_timer",
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.sleep_timer.assert_called_once()


async def test_clear_sleep_timer(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test the clear sleep timer action."""

    player_mocks.player_data.player.sleep_timer.side_effect = [15, 30, 45, 60, 90, 0]

    await hass.services.async_call(
        BLUESOUND_DOMAIN,
        "clear_sleep_timer",
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data.player.sleep_timer.assert_has_calls([call()] * 6)


async def test_join_cannot_join_to_self(
    hass: HomeAssistant, setup_config_entry: None, player_mocks: PlayerMocks
) -> None:
    """Test that joining to self is not allowed."""
    with pytest.raises(ServiceValidationError) as exc:
        await hass.services.async_call(
            BLUESOUND_DOMAIN,
            "join",
            {
                ATTR_ENTITY_ID: "media_player.player_name1111",
                "master": "media_player.player_name1111",
            },
            blocking=True,
        )

    assert str(exc.value) == "Cannot join player to itself"


async def test_join(
    hass: HomeAssistant,
    setup_config_entry: None,
    setup_config_entry_secondary: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test the join action."""
    await hass.services.async_call(
        BLUESOUND_DOMAIN,
        "join",
        {
            ATTR_ENTITY_ID: "media_player.player_name1111",
            "master": "media_player.player_name2222",
        },
        blocking=True,
    )

    player_mocks.player_data_secondary.player.add_slave.assert_called_once_with(
        "1.1.1.1", 11000
    )


async def test_unjoin(
    hass: HomeAssistant,
    setup_config_entry: None,
    setup_config_entry_secondary: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test the unjoin action."""
    updated_sync_status = dataclasses.replace(
        player_mocks.player_data.sync_long_polling_mock.get(),
        master=PairedPlayer("2.2.2.2", 11000),
    )
    player_mocks.player_data.sync_long_polling_mock.set(updated_sync_status)

    # give the long polling loop a chance to update the state; this could be any async call
    await hass.async_block_till_done()

    await hass.services.async_call(
        BLUESOUND_DOMAIN,
        "unjoin",
        {ATTR_ENTITY_ID: "media_player.player_name1111"},
        blocking=True,
    )

    player_mocks.player_data_secondary.player.remove_slave.assert_called_once_with(
        "1.1.1.1", 11000
    )


async def test_attr_master(
    hass: HomeAssistant,
    setup_config_entry: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test the media player master."""
    attr_master = hass.states.get("media_player.player_name1111").attributes["master"]
    assert attr_master is False

    updated_sync_status = dataclasses.replace(
        player_mocks.player_data.sync_long_polling_mock.get(),
        slaves=[PairedPlayer("2.2.2.2", 11000)],
    )
    player_mocks.player_data.sync_long_polling_mock.set(updated_sync_status)

    # give the long polling loop a chance to update the state; this could be any async call
    await hass.async_block_till_done()

    attr_master = hass.states.get("media_player.player_name1111").attributes["master"]

    assert attr_master is True


async def test_attr_bluesound_group(
    hass: HomeAssistant,
    setup_config_entry: None,
    setup_config_entry_secondary: None,
    player_mocks: PlayerMocks,
) -> None:
    """Test the media player grouping."""
    attr_bluesound_group = hass.states.get(
        "media_player.player_name1111"
    ).attributes.get("bluesound_group")
    assert attr_bluesound_group is None

    updated_status = dataclasses.replace(
        player_mocks.player_data.status_long_polling_mock.get(),
        group_name="player-name1111+player-name2222",
    )
    player_mocks.player_data.status_long_polling_mock.set(updated_status)

    # give the long polling loop a chance to update the state; this could be any async call
    await hass.async_block_till_done()

    attr_bluesound_group = hass.states.get(
        "media_player.player_name1111"
    ).attributes.get("bluesound_group")

    assert attr_bluesound_group == ["player-name1111", "player-name2222"]
