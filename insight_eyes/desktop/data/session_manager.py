# -*- coding: utf-8 -*-
"""
监控会话管理器
支持删除单个或批量删除监控会话
"""
from typing import List, Dict, Optional
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from logzero import logger

from .database import DatabaseManager


class SessionManager(QObject):
    """监控会话管理器 - 支持删除操作"""

    # 信号
    session_deleted = pyqtSignal(int)  # session_id
    sessions_deleted = pyqtSignal(list)  # session_ids
    delete_failed = pyqtSignal(str)  # error_message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()

    def delete_session(self, session_id: int, emit_signal: bool = True) -> bool:
        """
        删除单个监控会话

        Args:
            session_id: 会话ID
            emit_signal: 是否发射信号（批量删除时设为False避免多次弹窗）

        Returns:
            bool: 删除是否成功

        删除步骤：
        1. 删除指标样本数据（performance_metrics 表）
        2. 删除告警记录（alerts 表）
        3. 删除会话记录（monitoring_sessions 表）
        4. 发送 session_deleted 信号（如果 emit_signal=True）
        """
        try:
            # 验证会话是否存在
            session = self.db.get_session(session_id)
            if not session:
                error_msg = f"会话 {session_id} 不存在"
                logger.warning(error_msg)
                self.delete_failed.emit(error_msg)
                return False

            logger.info(f"开始删除会话 {session_id}")

            # 使用数据库事务
            conn = self.db.get_connection()
            cursor = conn.cursor()

            try:
                # 开始事务
                cursor.execute("BEGIN TRANSACTION")

                # 1. 删除告警记录
                cursor.execute(
                    "DELETE FROM alerts WHERE session_id = ?",
                    (session_id,)
                )
                alerts_deleted = cursor.rowcount
                logger.debug(f"会话 {session_id}: 删除了 {alerts_deleted} 条告警记录")

                # 2. 删除指标样本数据
                cursor.execute(
                    "DELETE FROM performance_metrics WHERE session_id = ?",
                    (session_id,)
                )
                metrics_deleted = cursor.rowcount
                logger.debug(f"会话 {session_id}: 删除了 {metrics_deleted} 条指标样本")

                # 3. 删除会话记录
                cursor.execute(
                    "DELETE FROM monitoring_sessions WHERE id = ?",
                    (session_id,)
                )
                sessions_deleted = cursor.rowcount
                logger.debug(f"会话 {session_id}: 删除了 {sessions_deleted} 条会话记录")

                # 提交事务
                conn.commit()

                logger.info(f"成功删除会话 {session_id}: {alerts_deleted} 条告警, {metrics_deleted} 条指标")

                # 只在需要时发送信号（避免批量删除时多次弹窗）
                if emit_signal:
                    self.session_deleted.emit(session_id)

                return True

            except Exception as e:
                # 回滚事务
                conn.rollback()
                error_msg = f"删除会话 {session_id} 时发生错误，已回滚: {e}"
                logger.error(error_msg)
                self.delete_failed.emit(error_msg)
                return False

        except Exception as e:
            error_msg = f"删除会话失败: {e}"
            logger.error(error_msg)
            self.delete_failed.emit(error_msg)
            return False

    def delete_sessions(self, session_ids: List[int]) -> Dict[str, int]:
        """
        批量删除监控会话（优化版：只发射一次信号，避免多次弹窗）

        Args:
            session_ids: 会话ID列表

        Returns:
            Dict: {'success': 成功数, 'failed': 失败数, 'failed_ids': 失败的ID列表}
        """
        success_count = 0
        failed_count = 0
        failed_ids = []
        successfully_deleted_ids = []

        logger.info(f"开始批量删除 {len(session_ids)} 个会话")

        for session_id in session_ids:
            # 关键修改：传入 emit_signal=False，避免为每个会话发射信号
            if self.delete_session(session_id, emit_signal=False):
                success_count += 1
                successfully_deleted_ids.append(session_id)
            else:
                failed_count += 1
                failed_ids.append(session_id)

        result = {
            'success': success_count,
            'failed': failed_count,
            'failed_ids': failed_ids
        }

        logger.info(f"批量删除完成: 成功 {success_count}, 失败 {failed_count}")

        # 只发送一次批量删除信号（包含所有成功删除的会话ID）
        if successfully_deleted_ids:
            self.sessions_deleted.emit(successfully_deleted_ids)

        return result

    def get_session_stats(self, session_id: int) -> Optional[Dict]:
        """
        获取会话统计信息（用于导出）

        Args:
            session_id: 会话ID

        Returns:
            Dict: 会话统计信息，失败返回 None
        """
        try:
            session = self.db.get_session(session_id)
            if not session:
                return None

            # 获取指标样本数
            metrics = self.db.get_metrics(session_id)
            metrics_count = len(metrics) if metrics else 0

            # 获取告警数
            alerts = self.db.get_alerts(session_id=session_id)
            alerts_count = len(alerts) if alerts else 0

            return {
                'session_id': session_id,
                'device_id': session['device_id'],
                'package_name': session['package_name'],
                'start_time': session['start_time'],
                'end_time': session.get('end_time'),
                'metrics_count': metrics_count,
                'alerts_count': alerts_count,
                'sample_interval': session.get('sample_interval', 1000)
            }

        except Exception as e:
            logger.error(f"获取会话统计失败: {e}")
            return None

    def cleanup_old_sessions(self, keep_days: int = 30) -> int:
        """
        清理旧会话（删除指定天数之前的会话）

        Args:
            keep_days: 保留天数，默认30天

        Returns:
            int: 删除的会话数量
        """
        try:
            from datetime import datetime, timedelta

            # 计算截止日期
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            cutoff_str = cutoff_date.isoformat()

            # 查询需要删除的会话
            query = """
                SELECT id FROM monitoring_sessions
                WHERE start_time < ? AND end_time IS NOT NULL
                ORDER BY start_time
            """

            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (cutoff_str,))
            old_sessions = cursor.fetchall()

            if not old_sessions:
                logger.info(f"没有需要清理的会话（保留 {keep_days} 天内的数据）")
                return 0

            session_ids = [row[0] for row in old_sessions]
            logger.info(f"发现 {len(session_ids)} 个超过 {keep_days} 天的旧会话")

            # 批量删除
            result = self.delete_sessions(session_ids)

            return result['success']

        except Exception as e:
            logger.error(f"清理旧会话失败: {e}")
            return 0

    def get_storage_size(self) -> Dict[str, int]:
        """
        获取数据库存储大小统计

        Returns:
            Dict: {'sessions': 会话数, 'metrics': 指标样本数, 'alerts': 告警数}
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 统计会话数
            cursor.execute("SELECT COUNT(*) FROM monitoring_sessions")
            sessions_count = cursor.fetchone()[0]

            # 统计指标样本数
            cursor.execute("SELECT COUNT(*) FROM performance_metrics")
            metrics_count = cursor.fetchone()[0]

            # 统计告警数
            cursor.execute("SELECT COUNT(*) FROM alerts")
            alerts_count = cursor.fetchone()[0]

            return {
                'sessions': sessions_count,
                'metrics': metrics_count,
                'alerts': alerts_count
            }

        except Exception as e:
            logger.error(f"获取存储大小失败: {e}")
            return {'sessions': 0, 'metrics': 0, 'alerts': 0}
