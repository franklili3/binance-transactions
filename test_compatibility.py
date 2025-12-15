#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 3.10兼容性测试脚本
用于验证所有依赖和功能是否正常工作
"""

import sys
import os
import subprocess
from datetime import datetime

def test_python_version():
    """测试Python版本"""
    print(f"Python版本: {sys.version}")
    if sys.version_info >= (3, 10):
        print("✅ Python版本兼容 (>= 3.10)")
        return True
    else:
        print("⚠️  建议使用Python 3.10或更高版本")
        return False

def install_dependencies():
    """安装依赖包"""
    print("📦 检测到缺少依赖包，正在安装...")
    
    try:
        # 检查requirements.txt是否存在
        if os.path.exists('requirements.txt'):
            print("📋 从requirements.txt安装依赖...")
            print(f"🐍 使用Python解释器: {sys.executable}")
            
            # 使用当前Python解释器的pip模块安装
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], capture_output=True, text=True)
            
            print(f"📤 安装输出: {result.stdout}")
            if result.stderr:
                print(f"⚠️  警告信息: {result.stderr}")
            
            if result.returncode == 0:
                print("✅ 依赖安装成功")
                return True
            else:
                print(f"❌ 依赖安装失败: {result.stderr}")
                return False
        else:
            print("❌ requirements.txt文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ 安装依赖时出错: {e}")
        return False

def test_imports():
    """测试所有必要的导入"""
    missing_deps = []
    
    try:
        import pandas as pd
        print(f"✅ pandas {pd.__version__}")
    except ImportError as e:
        print(f"❌ pandas导入失败: {e}")
        missing_deps.append('pandas')
    
    try:
        import numpy as np
        print(f"✅ numpy {np.__version__}")
    except ImportError as e:
        print(f"❌ numpy导入失败: {e}")
        missing_deps.append('numpy')
    
    try:
        import ccxt
        print(f"✅ ccxt {ccxt.__version__}")
    except ImportError as e:
        print(f"❌ ccxt导入失败: {e}")
        missing_deps.append('ccxt')
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError as e:
        print(f"❌ python-dotenv导入失败: {e}")
        missing_deps.append('python-dotenv')
    
    # 如果有缺失的依赖，尝试安装
    if missing_deps:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_deps)}")
        if install_dependencies():
            print("🔄 重新测试导入...")
            # 重新测试导入
            return test_imports_after_install()
        else:
            return False
    
    return True

def test_imports_after_install():
    """安装后重新测试导入"""
    try:
        import pandas as pd
        print(f"✅ pandas {pd.__version__}")
    except ImportError:
        print("❌ pandas安装后仍无法导入")
        return False
    
    try:
        import numpy as np
        print(f"✅ numpy {np.__version__}")
    except ImportError:
        print("❌ numpy安装后仍无法导入")
        return False
    
    try:
        import ccxt
        print(f"✅ ccxt {ccxt.__version__}")
    except ImportError:
        print("❌ ccxt安装后仍无法导入")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv安装后仍无法导入")
        return False
    
    return True

def test_pandas_functionality():
    """测试pandas功能"""
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # 测试DataFrame创建
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=5, freq='D'),
            'symbol': ['BTC/USDT'] * 5,
            'amount': np.random.randn(5),
            'price': np.random.randn(5) + 50000,
            'side': ['buy', 'sell', 'buy', 'sell', 'buy']
        })
        
        # 测试时间操作
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # 测试groupby操作
        df['date_only'] = df.index.date
        grouped = df.groupby('date_only')
        df.drop('date_only', axis=1, inplace=True)
        
        print("✅ pandas功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ pandas功能测试失败: {e}")
        return False

def test_ccxt_functionality():
    """测试ccxt功能（不需要API密钥）"""
    try:
        import ccxt
        
        # 测试ccxt基本功能
        exchange = ccxt.binance({
            'sandbox': True,
            'enableRateLimit': True,
        })
        
        # 测试加载市场（不需要认证）
        markets = exchange.load_markets()
        print(f"✅ ccxt功能测试通过，加载了 {len(markets)} 个交易对")
        return True
        
    except Exception as e:
        print(f"❌ ccxt功能测试失败: {e}")
        return False

def test_env_file():
    """测试.env文件"""
    if os.path.exists('.env'):
        print("✅ .env文件存在")
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            
            if api_key and secret_key:
                print("✅ .env文件配置正确")
            else:
                print("⚠️  .env文件存在但API密钥未配置")
            
            return True
        except Exception as e:
            print(f"❌ .env文件读取失败: {e}")
            return False
    else:
        print("⚠️  .env文件不存在，请复制.env.example并配置")
        return False

def test_main_class():
    """测试主类的基本功能"""
    try:
        from binance_copy_trade_transactions import BinanceCopyTradeTransactions
        
        # 不创建实例，只测试导入
        print("✅ 主类导入成功")
        return True
        
    except ImportError as e:
        print(f"❌ 主类导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 主类测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("Python 3.10兼容性测试")
    print("=" * 60)
    
    tests = [
        ("Python版本", test_python_version),
        ("依赖导入", test_imports),
        ("pandas功能", test_pandas_functionality),
        ("ccxt功能", test_ccxt_functionality),
        ("环境配置", test_env_file),
        ("主类导入", test_main_class),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 测试: {test_name}")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ 通过" if results[i] else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！项目兼容Python 3.10")
        return True
    else:
        print("⚠️  部分测试失败，请检查上述问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
