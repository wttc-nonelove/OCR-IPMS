#!/usr/bin/env python3
"""生成新的 Alembic 迁移脚本

用法:
    python scripts/new_migration.py "描述信息"
"""
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/new_migration.py \"迁移描述\"")
        sys.exit(1)

    message = sys.argv[1]
    backend_dir = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"生成迁移失败:\n{result.stderr}")
        sys.exit(1)

    print(result.stdout)
    print("迁移脚本已生成，请检查 alembic/versions/ 目录")


if __name__ == "__main__":
    main()
