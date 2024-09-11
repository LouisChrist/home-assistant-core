"""Tests for the Bluesound Media Player platform."""

import asyncio
import dataclasses

from pyblu import Player, Status
from pyblu.errors import PlayerUnreachableError

from homeassistant.components.media_player import MediaPlayerState
from homeassistant.core import HomeAssistant

from .utils import ValueStore


async def test_pause(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player pause."""
    await hass.services.async_call(
        "media_player",
        "media_pause",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.pause.assert_called_once()


async def test_play(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player play."""
    await hass.services.async_call(
        "media_player",
        "media_play",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.play.assert_called_once()


async def test_next_track(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player next track."""
    await hass.services.async_call(
        "media_player",
        "media_next_track",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.skip.assert_called_once()


async def test_previous_track(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player previous track."""
    await hass.services.async_call(
        "media_player",
        "media_previous_track",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.back.assert_called_once()


async def test_volume_set(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player volume set."""
    await hass.services.async_call(
        "media_player",
        "volume_set",
        {"entity_id": "media_player.player_name", "volume_level": 0.5},
        blocking=True,
    )

    player.volume.assert_called_once_with(50)


async def test_volume_mute(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player volume mute."""
    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {"entity_id": "media_player.player_name", "is_volume_muted": True},
        blocking=True,
    )

    player.volume.assert_called_once_with(mute=True)


async def test_volume_up(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player volume up."""
    await hass.services.async_call(
        "media_player",
        "volume_up",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.volume.assert_called_once_with(11)


async def test_volume_down(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player volume down."""
    await hass.services.async_call(
        "media_player",
        "volume_down",
        {"entity_id": "media_player.player_name"},
        blocking=True,
    )

    player.volume.assert_called_once_with(9)


async def test_attributes_set(
    hass: HomeAssistant, setup_config_entry: None, player: Player
) -> None:
    """Test the media player attributes set."""
    state = hass.states.get("media_player.player_name")
    assert state.state == "playing"
    assert state.attributes["volume_level"] == 0.1
    assert state.attributes["is_volume_muted"] is False
    assert state.attributes["media_content_type"] == "music"
    assert state.attributes["media_position"] == 2
    assert state.attributes["shuffle"] is False
    assert state.attributes["master"] is False
    assert state.attributes["friendly_name"] == "player-name"
    assert state.attributes["media_title"] == "song"
    assert state.attributes["media_artist"] == "artist"
    assert state.attributes["media_album_name"] == "album"


async def test_status_updated(
    hass: HomeAssistant,
    setup_config_entry: None,
    player: Player,
    status_store: ValueStore[Status],
) -> None:
    """Test the media player status updated."""
    pre_state = hass.states.get("media_player.player_name")
    assert pre_state.state == "playing"
    assert pre_state.attributes["volume_level"] == 0.1

    status = status_store.get()
    status = dataclasses.replace(status, state="pause", volume=50, etag="changed")
    status_store.set(status)

    await asyncio.sleep(0)
    for _ in range(10):
        post_state = hass.states.get("media_player.player_name")
        if post_state.state == MediaPlayerState.PAUSED:
            break
        await asyncio.sleep(1)

    assert post_state.state == MediaPlayerState.PAUSED
    assert post_state.attributes["volume_level"] == 0.5


async def test_unavailable_when_offline(
    hass: HomeAssistant,
    setup_config_entry: None,
    player: Player,
    status_store: ValueStore[Status],
) -> None:
    """Test that the media player goes unavailable when the player is unreachable."""
    pre_state = hass.states.get("media_player.player_name")
    assert pre_state.state == "playing"

    player.status.side_effect = PlayerUnreachableError("Player not reachable")
    status_store.trigger()

    await asyncio.sleep(0)
    for _ in range(10):
        post_state = hass.states.get("media_player.player_name")
        if post_state.state == "unavailable":
            break
        await asyncio.sleep(1)

    assert post_state.state == "unavailable"
