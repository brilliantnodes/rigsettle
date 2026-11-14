"""Shared helpers for direct mode tests."""


def to_hex(addr_bytes):
    """Convert address bytes to checksummed hex matching contract output.

    The contract's get_bets()/get_points() return keys via Address.as_hex,
    which produces EIP-55 checksummed hex. Call after direct_deploy so the
    SDK is on sys.path.
    """
    if hasattr(addr_bytes, "as_hex"):
        return addr_bytes.as_hex
    from genlayer.py.types import Address

    return Address(addr_bytes).as_hex


# genlayer-test 0.29.2: VMContext.warp() updates its own clock but its
# _refresh_gl_message() only copies the sender and origin into
# gl.message_raw, so contracts that read gl.message_raw["datetime"] keep
# seeing the deploy time. Copy the clock (and value) across as well.
def _patch_warp():
    from gltest.direct import vm as _vm

    original = _vm.VMContext._refresh_gl_message
    if getattr(original, "_rigsettle_patched", False):
        return

    def refresh(self):
        original(self)
        import sys as _sys

        gl = _sys.modules.get("genlayer.gl")
        if gl is not None and getattr(gl, "message_raw", None) is not None:
            gl.message_raw["datetime"] = self._datetime
            gl.message_raw["value"] = self._value

    refresh._rigsettle_patched = True
    _vm.VMContext._refresh_gl_message = refresh


_patch_warp()
