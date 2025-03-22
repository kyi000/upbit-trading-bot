"""
기술적 지표 계산 모듈
"""

import logging
import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    기술적 지표 계산 클래스
    """
    
    @staticmethod
    def add_indicators(df, config):
        """
        데이터프레임에 여러 기술적 지표를 추가하는 메서드
        
        Args:
            df (pd.DataFrame): OHLCV 데이터프레임
            config (dict): 지표 설정
            
        Returns:
            pd.DataFrame: 지표가 추가된 데이터프레임
        """
        # 데이터프레임 복사본 생성
        df = df.copy()
        
        try:
            # 이동평균선
            if config['ma_crossover']['enabled']:
                df = TechnicalIndicators.add_moving_average(
                    df,
                    short_period=config['ma_crossover']['short_period'],
                    long_period=config['ma_crossover']['long_period'],
                    trend_period=config['ma_crossover']['trend_period']
                )
                
            # RSI
            if config['rsi']['enabled']:
                df = TechnicalIndicators.add_rsi(
                    df,
                    period=config['rsi']['period']
                )
                
                # RSI 다이버전스
                if config['rsi']['use_divergence']:
                    df = TechnicalIndicators.add_rsi_divergence(df)
                
            # 볼린저 밴드
            if config['bollinger']['enabled']:
                df = TechnicalIndicators.add_bollinger_bands(
                    df,
                    period=config['bollinger']['period'],
                    std_dev=config['bollinger']['std_dev']
                )
                
            # 거래량 분석
            if config['volume']['enabled']:
                df = TechnicalIndicators.add_volume_indicators(
                    df,
                    period=config['volume']['period'],
                    surge_threshold=config['volume']['surge_threshold']
                )
                
            # NaN 값 처리
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"지표 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def add_moving_average(df, short_period=9, long_period=21, trend_period=50):
        """
        데이터프레임에 이동평균선을 추가하는 메서드
        
        Args:
            df (pd.DataFrame): OHLCV 데이터프레임
            short_period (int): 단기 이동평균선 기간
            long_period (int): 장기 이동평균선 기간
            trend_period (int): 추세 이동평균선 기간
            
        Returns:
            pd.DataFrame: 이동평균선이 추가된 데이터프레임
        """
        try:
            # 단기 이동평균선
            df[f'ma{short_period}'] = df['close'].rolling(window=short_period).mean()
            
            # 장기 이동평균선
            df[f'ma{long_period}'] = df['close'].rolling(window=long_period).mean()
            
            # 추세 이동평균선
            df[f'ma{trend_period}'] = df['close'].rolling(window=trend_period).mean()
            
            # 골든 크로스 / 데드 크로스 신호
            df['ma_cross_signal'] = 0
            
            # 단기선이 장기선을 상향 돌파할 때 (골든 크로스): 1
            golden_cross = (df[f'ma{short_period}'].shift(1) <= df[f'ma{long_period}'].shift(1)) & \
                           (df[f'ma{short_period}'] > df[f'ma{long_period}'])
            df.loc[golden_cross, 'ma_cross_signal'] = 1
            
            # 단기선이 장기선을 하향 돌파할 때 (데드 크로스): -1
            dead_cross = (df[f'ma{short_period}'].shift(1) >= df[f'ma{long_period}'].shift(1)) & \
                         (df[f'ma{short_period}'] < df[f'ma{long_period}'])
            df.loc[dead_cross, 'ma_cross_signal'] = -1
            
            # 추세 방향
            df['trend_direction'] = np.where(df['close'] > df[f'ma{trend_period}'], 1, -1)
            
            return df
            
        except Exception as e:
            logger.error(f"이동평균선 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def add_rsi(df, period=14):
        """
        데이터프레임에 RSI를 추가하는 메서드
        
        Args:
            df (pd.DataFrame): OHLCV 데이터프레임
            period (int): RSI 계산 기간
            
        Returns:
            pd.DataFrame: RSI가 추가된 데이터프레임
        """
        try:
            # pandas_ta를 사용하여 RSI 계산
            df[f'rsi{period}'] = ta.rsi(df['close'], length=period)
            
            # RSI 신호
            df['rsi_signal'] = 0
            
            # 과매도 상태에서 회복(매수 신호): 1
            oversold_recovery = (df[f'rsi{period}'].shift(1) < 30) & (df[f'rsi{period}'] >= 30)
            df.loc[oversold_recovery, 'rsi_signal'] = 1
            
            # 과매수 상태에서 반락(매도 신호): -1
            overbought_fall = (df[f'rsi{period}'].shift(1) > 70) & (df[f'rsi{period}'] <= 70)
            df.loc[overbought_fall, 'rsi_signal'] = -1
            
            return df
            
        except Exception as e:
            logger.error(f"RSI 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def add_rsi_divergence(df, period=14, window=10):
        """
        데이터프레임에 RSI 다이버전스를 추가하는 메서드
        
        Args:
            df (pd.DataFrame): RSI가 포함된 데이터프레임
            period (int): RSI 계산 기간
            window (int): 다이버전스 확인 윈도우 크기
            
        Returns:
            pd.DataFrame: RSI 다이버전스가 추가된 데이터프레임
        """
        try:
            rsi_col = f'rsi{period}'
            
            if rsi_col not in df.columns:
                logger.warning(f"RSI {period} 칼럼이 없습니다. 먼저 add_rsi() 메서드를 호출하세요.")
                return df
                
            df['rsi_divergence'] = 0
            
            # 상승 다이버전스 (가격 하락, RSI 상승 = 매수 신호)
            for i in range(window, len(df)):
                if df['close'].iloc[i] < df['close'].iloc[i-window] and \
                   df[rsi_col].iloc[i] > df[rsi_col].iloc[i-window]:
                    df.loc[df.index[i], 'rsi_divergence'] = 1
                    
            # 하락 다이버전스 (가격 상승, RSI 하락 = 매도 신호)
            for i in range(window, len(df)):
                if df['close'].iloc[i] > df['close'].iloc[i-window] and \
                   df[rsi_col].iloc[i] < df[rsi_col].iloc[i-window]:
                    df.loc[df.index[i], 'rsi_divergence'] = -1
            
            return df
            
        except Exception as e:
            logger.error(f"RSI 다이버전스 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def add_bollinger_bands(df, period=20, std_dev=2.0):
        """
        데이터프레임에 볼린저 밴드를 추가하는 메서드
        
        Args:
            df (pd.DataFrame): OHLCV 데이터프레임
            period (int): 볼린저 밴드 계산 기간
            std_dev (float): 표준편차 승수
            
        Returns:
            pd.DataFrame: 볼린저 밴드가 추가된 데이터프레임
        """
        try:
            # 중심선 (단순 이동평균)
            df['bb_middle'] = df['close'].rolling(window=period).mean()
            
            # 표준편차
            df['bb_std'] = df['close'].rolling(window=period).std()
            
            # 상단 밴드
            df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
            
            # 하단 밴드
            df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
            
            # 밴드 폭 (Bandwidth)
            df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # 볼린저 밴드 신호
            df['bb_signal'] = 0
            
            # 하단 밴드 터치 후 반등 (매수 신호)
            touch_lower = (df['close'].shift(1) <= df['bb_lower'].shift(1)) & \
                          (df['close'] > df['bb_lower']) & \
                          (df['close'] > df['close'].shift(1))
            df.loc[touch_lower, 'bb_signal'] = 1
            
            # 상단 밴드 터치 후 하락 (매도 신호)
            touch_upper = (df['close'].shift(1) >= df['bb_upper'].shift(1)) & \
                          (df['close'] < df['bb_upper']) & \
                          (df['close'] < df['close'].shift(1))
            df.loc[touch_upper, 'bb_signal'] = -1
            
            return df
            
        except Exception as e:
            logger.error(f"볼린저 밴드 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def add_volume_indicators(df, period=20, surge_threshold=2.0):
        """
        데이터프레임에 거래량 지표를 추가하는 메서드
        
        Args:
            df (pd.DataFrame): OHLCV 데이터프레임
            period (int): 거래량 이동평균 기간
            surge_threshold (float): 거래량 급증 기준 배수
            
        Returns:
            pd.DataFrame: 거래량 지표가 추가된 데이터프레임
        """
        try:
            # 거래량 이동평균
            df['volume_ma'] = df['volume'].rolling(window=period).mean()
            
            # 거래량 비율 (현재 거래량 / 이동평균)
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # 거래량 급증 여부
            df['volume_surge'] = df['volume_ratio'] > surge_threshold
            
            # 거래량 신호
            df['volume_signal'] = 0
            
            # 거래량 급증 + 가격 상승 = 매수 신호
            volume_price_up = df['volume_surge'] & (df['close'] > df['close'].shift(1))
            df.loc[volume_price_up, 'volume_signal'] = 1
            
            # 거래량 급증 + 가격 하락 = 매도 신호
            volume_price_down = df['volume_surge'] & (df['close'] < df['close'].shift(1))
            df.loc[volume_price_down, 'volume_signal'] = -1
            
            return df
            
        except Exception as e:
            logger.error(f"거래량 지표 계산 중 오류 발생: {e}")
            return df
    
    @staticmethod
    def get_combined_signal(df):
        """
        여러 기술적 지표의 신호를 종합하여 최종 신호를 생성하는 메서드
        
        Args:
            df (pd.DataFrame): 기술적 지표가 추가된 데이터프레임
            
        Returns:
            pd.Series: 종합 신호 (1: 매수, -1: 매도, 0: 관망)
        """
        signals = []
        weights = []
        
        # 각 신호 확인 및 가중치 부여
        if 'ma_cross_signal' in df.columns:
            signals.append(df['ma_cross_signal'])
            weights.append(0.3)  # 이동평균선 교차 가중치
            
        if 'rsi_signal' in df.columns:
            signals.append(df['rsi_signal'])
            weights.append(0.2)  # RSI 신호 가중치
            
        if 'rsi_divergence' in df.columns:
            signals.append(df['rsi_divergence'])
            weights.append(0.15)  # RSI 다이버전스 가중치
            
        if 'bb_signal' in df.columns:
            signals.append(df['bb_signal'])
            weights.append(0.2)  # 볼린저 밴드 신호 가중치
            
        if 'volume_signal' in df.columns:
            signals.append(df['volume_signal'])
            weights.append(0.15)  # 거래량 신호 가중치
        
        # 가중합 계산
        if signals:
            weighted_signal = sum(signal * weight for signal, weight in zip(signals, weights))
            
            # 신호 이산화 (threshold: ±0.3)
            combined_signal = np.zeros_like(weighted_signal)
            combined_signal[weighted_signal > 0.3] = 1  # 매수 신호
            combined_signal[weighted_signal < -0.3] = -1  # 매도 신호
            
            return pd.Series(combined_signal, index=df.index)
        else:
            return pd.Series(0, index=df.index)  # 신호가 없는 경우 관망