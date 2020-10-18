# -*- mode: python ; coding: utf-8 -*-
import sys
sys.setrecursionlimit(5000) # or more
block_cipher = None


a = Analysis(['C:\\Users\\rhohe\\PycharmProjects\\cmdTestSequence\\src\\main_sequence.py'],
             pathex=['C:\\Users\\rhohe\\PycharmProjects\\cmdTestSequence\\bin\\PItest'],
             binaries=[],
             datas=[('C:\\Users\\rhohe\\PycharmProjects\\cmdTestSequence\\src\\config\\test-details.csv', 'config')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='main_sequence',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
