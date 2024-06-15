# -*- coding: UTF-8 -*-

# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

"""zipalign
modified from https://github.com/obfusk/reproducible-apk-tools/blob/master/zipalign.py
"""

from __future__ import print_function

import os
import struct
import sys
import zipfile

from collections import namedtuple

ZipData = namedtuple("ZipData", ("cd_offset", "eocd_offset", "cd_and_eocd"))

DEFAULT_PAGE_SIZE = 4


class Error(RuntimeError):
    pass


def bytes_to_int(byte_data, byte_order='big'):
    fmt = '>' if byte_order == 'big' else '<'
    fmt += {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}[len(byte_data)]
    return struct.unpack(fmt, byte_data)[0]


def int_to_bytes(integer, length, byte_order='big'):
    fmt = '>' if byte_order == 'big' else '<'
    fmt += {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}[length]
    return struct.pack(fmt, integer)


def zipalign(
    input_apk,
    output_apk,
    page_align=False,
    page_size=None,
    pad_like_apksigner=False,
    copy_extra=False,
    update_lfh=True,
):
    with zipfile.ZipFile(input_apk, "r") as zf:
        infos = zf.infolist()
    zdata = zip_data(input_apk)
    offsets = {}
    with open(input_apk, "rb") as fhi, open(output_apk, "w+b") as fho:
        for info in sorted(infos, key=lambda info: info.header_offset):
            off_i = fhi.tell()
            if info.header_offset > off_i:
                extra_bytes = info.header_offset - off_i
                if copy_extra:
                    fho.write(fhi.read(extra_bytes))
                else:
                    fhi.seek(extra_bytes, os.SEEK_CUR)
            hdr = fhi.read(30)
            if hdr[:4] != b"\x50\x4b\x03\x04":
                raise Error("Expected local file header signature")
            n, m = struct.unpack("<HH", hdr[26:30])
            hdr += fhi.read(n + m)
            if info.filename in offsets:
                raise Error("Duplicate ZIP entry: %s" % info.filename)
            offsets[info.filename] = off_o = fho.tell()
            if info.compress_type == 0:
                hdr = _align_zip_entry(
                    info,
                    hdr,
                    n,
                    m,
                    off_o,
                    page_align=page_align,
                    page_size=page_size,
                    pad_like_apksigner=pad_like_apksigner,
                )
            if info.flag_bits & 0x08:
                fhi.seek(info.compress_size, os.SEEK_CUR)
                data_descriptor = fhi.read(12)
                if data_descriptor[:4] == b"\x50\x4b\x07\x08":
                    data_descriptor += fhi.read(4)
                fhi.seek(-(info.compress_size + len(data_descriptor)), os.SEEK_CUR)
                if update_lfh:
                    hdr = hdr[:14] + data_descriptor[-12:] + hdr[26:]
            else:
                data_descriptor = b""
            fho.write(hdr)
            _copy_bytes(fhi, fho, info.compress_size + len(data_descriptor))
        extra_bytes = zdata.cd_offset - fhi.tell()
        if copy_extra:
            _copy_bytes(fhi, fho, extra_bytes)
        else:
            fhi.seek(extra_bytes, os.SEEK_CUR)
        cd_offset = fho.tell()
        for info in infos:
            hdr = fhi.read(46)
            if hdr[:4] != b"\x50\x4b\x01\x02":
                raise Error("Expected central directory file header signature")
            n, m, k = struct.unpack("<HHH", hdr[28:34])
            hdr += fhi.read(n + m + k)
            off = int_to_bytes(offsets[info.filename], 4, "little")
            hdr = hdr[:42] + off + hdr[46:]
            fho.write(hdr)
        eocd_offset = fho.tell()
        fho.write(zdata.cd_and_eocd[zdata.eocd_offset - zdata.cd_offset :])
        fho.seek(eocd_offset + 8)
        fho.write(
            struct.pack(
                "<HHLL", len(offsets), len(offsets), eocd_offset - cd_offset, cd_offset
            )
        )


# NB: doesn't sync local & CD headers!
def _align_zip_entry(
    info, hdr, n, m, off_o, page_align=False, page_size=None, pad_like_apksigner=False,
):
    psize = DEFAULT_PAGE_SIZE if page_size is None else page_size
    align = psize * 1024 if page_align and info.filename.endswith(".so") else 4
    new_off = 30 + n + m + off_o
    old_xtr = hdr[30 + n : 30 + n + m]
    new_xtr = b""
    while len(old_xtr) >= 4:
        hdr_id, size = struct.unpack("<HH", old_xtr[:4])
        if size > len(old_xtr) - 4:
            break
        if not (hdr_id == 0 and size == 0):
            if hdr_id == 0xD935:
                if size >= 2:
                    align = bytes_to_int(old_xtr[4:6], "little")
            else:
                new_xtr += old_xtr[: size + 4]
        old_xtr = old_xtr[size + 4 :]
    if new_off % align != 0:
        if pad_like_apksigner:
            pad = (align - (new_off - m + len(new_xtr) + 6) % align) % align
            xtr = new_xtr + struct.pack("<HHH", 0xD935, 2 + pad, align) + pad * b"\x00"
        else:
            pad = (align - (new_off - m + len(new_xtr)) % align) % align
            xtr = new_xtr + pad * b"\x00"
        m_b = int_to_bytes(len(xtr), 2, "little")
        hdr = hdr[:28] + m_b + hdr[30 : 30 + n] + xtr
    return hdr


def _copy_bytes(fhi, fho, size, blocksize=4096):
    while size > 0:
        data = fhi.read(min(size, blocksize))
        if not data:
            break
        size -= len(data)
        fho.write(data)
    if size != 0:
        raise Error("Unexpected EOF")


def zip_data(apkfile, count=1024):
    with open(apkfile, "rb") as fh:
        fh.seek(-min(os.path.getsize(apkfile), count), os.SEEK_END)
        data = fh.read()
        pos = data.rfind(b"\x50\x4b\x05\x06")
        if pos == -1:
            raise Error("Expected end of central directory record (EOCD)")
        fh.seek(pos - len(data), os.SEEK_CUR)
        eocd_offset = fh.tell()
        fh.seek(16, os.SEEK_CUR)
        cd_offset = bytes_to_int(fh.read(4), "little")
        fh.seek(cd_offset)
        cd_and_eocd = fh.read()
    return ZipData(cd_offset, eocd_offset, cd_and_eocd)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="zipalign.py")
    parser.add_argument(
        "-p",
        "--page-align",
        action="store_true",
        help="use 4096-byte memory page alignment for .so files",
    )
    parser.add_argument(
        "-P",
        "--page-size",
        metavar="N",
        type=int,
        help="use N*1024-byte memory page alignment for .so files",
    )
    parser.add_argument(
        "--pad-like-apksigner",
        action="store_true",
        help="use 0xd935 Android ZIP Alignment Extra Field " "instead of zero padding",
    )
    parser.add_argument(
        "--copy-extra", action="store_true", help="copy extra bytes between ZIP entries"
    )
    parser.add_argument(
        "--no-update-lfh",
        action="store_false",
        dest="update_lfh",
        help="don't update the LFH using the data descriptor",
    )
    parser.add_argument("align", metavar="ALIGN", nargs="?", type=int, default=4)
    parser.add_argument("input_apk", metavar="INPUT_APK")
    parser.add_argument("output_apk", metavar="OUTPUT_APK")
    args = parser.parse_args()
    if args.align != 4:
        raise Error("ALIGN must be 4")
    if args.page_size not in (None, 4, 16, 64):
        print("Warning: specified page size is not 4, 16, or 64 KiB", file=sys.stderr)
    zipalign(
        args.input_apk,
        args.output_apk,
        page_align=bool(args.page_align or args.page_size),
        page_size=args.page_size,
        pad_like_apksigner=args.pad_like_apksigner,
        copy_extra=args.copy_extra,
        update_lfh=args.update_lfh,
    )

