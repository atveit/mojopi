"""Tests for max_brain/error_messages.py."""
import sys
sys.path.insert(0, "src")


def test_module_importable():
    from max_brain import error_messages
    assert hasattr(error_messages, "friendly_mlx_error")
    assert hasattr(error_messages, "hint_for_cold_start")


def test_friendly_mlx_error_handles_validation_error():
    from max_brain.error_messages import friendly_mlx_error

    class FakeValidationError(Exception):
        pass
    exc = FakeValidationError("pydantic_core._pydantic_core.ValidationError: 1 validation error")
    msg = friendly_mlx_error(exc)
    assert "MAXModelConfig" in msg or "device" in msg.lower()


def test_friendly_mlx_error_handles_apple_gpu():
    from max_brain.error_messages import friendly_mlx_error
    exc = RuntimeError("external memory not supported on Apple GPU during topk")
    msg = friendly_mlx_error(exc)
    # At least one of the Apple-GPU-related mappings matches
    assert "MLX Metal" in msg or "mlx_backend" in msg or "topk" in msg.lower()


def test_friendly_mlx_error_handles_network():
    from max_brain.error_messages import friendly_mlx_error
    exc = ConnectionError("Connection error: failed to reach huggingface.co")
    msg = friendly_mlx_error(exc)
    assert "network" in msg.lower() or "internet" in msg.lower()


def test_friendly_mlx_error_handles_invalid_repo():
    from max_brain.error_messages import friendly_mlx_error

    class HFValidationError(Exception): pass
    exc = HFValidationError("HFValidationError: bad repo format")
    msg = friendly_mlx_error(exc)
    assert "repo" in msg.lower() or "model" in msg.lower()


def test_friendly_mlx_error_handles_disk_full():
    from max_brain.error_messages import friendly_mlx_error
    exc = OSError("No space left on device")
    msg = friendly_mlx_error(exc)
    assert "disk" in msg.lower() or "space" in msg.lower()


def test_friendly_mlx_error_falls_back_for_unknown():
    from max_brain.error_messages import friendly_mlx_error
    exc = RuntimeError("something totally novel happened here")
    msg = friendly_mlx_error(exc)
    assert "novel" in msg or "something" in msg
    assert "RuntimeError" in msg


def test_friendly_mlx_error_never_raises():
    from max_brain.error_messages import friendly_mlx_error

    class Weird:
        def __str__(self): raise RuntimeError("str failed")
        def __repr__(self): return "Weird()"
    # friendly_mlx_error must tolerate an object whose __str__ raises
    msg = friendly_mlx_error(Weird())
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_hint_for_cold_start_mentions_model():
    from max_brain.error_messages import hint_for_cold_start
    hint = hint_for_cold_start("mlx-community/gemma-4-e4b-it-4bit")
    assert "gemma-4-e4b" in hint


def test_list_known_errors_non_empty():
    from max_brain.error_messages import list_known_errors
    errors = list_known_errors()
    assert len(errors) > 0
    assert any("ValidationError" in e for e in errors)
