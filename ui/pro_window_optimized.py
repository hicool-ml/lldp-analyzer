    def _process_debug_log_queue(self):
        """
        Process debug log queue with batch insertion and rate limiting
        优化：批量插入减少GUI重绘，限制总字符数防止渲染卡顿
        """
        if not self.debug_log_queue:
            return

        # 优化1: 批量处理，减少GUI操作次数
        batch_size = 50  # 增加到50条，批量处理更高效
        processed = 0

        # 优化2: 限制队列最大长度，防止内存溢出
        if len(self.debug_log_queue) > 1000:
            # 保留最新的1000条，删除最旧的
            self.debug_log_queue = self.debug_log_queue[-1000:]

        # 优化3: 批量合并文本，一次性插入
        batch_messages = []
        while self.debug_log_queue and processed < batch_size:
            message = self.debug_log_queue.pop(0)
            batch_messages.append(message)
            processed += 1

        if not batch_messages:
            return

        # 优化4: 合并成大字符串，减少insertText调用
        combined_text = "\n".join(batch_messages) + "\n"

        # 优化5: 限制单次插入的最大字符数，防止渲染卡顿
        max_chars_per_insert = 10000  # 每次最多插入1万字符
        if len(combined_text) > max_chars_per_insert:
            combined_text = combined_text[-max_chars_per_insert:]

        # 批量插入
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # 应用格式
        format = QTextCharFormat()
        format.setForeground(QColor("#64748b"))
        cursor.insertText(combined_text, format)

        # 优化6: 限制总字符数，防止文档过大导致渲染慢
        max_total_chars = 100000  # 最多保留10万字符
        current_text = self.log_text.toPlainText()
        if len(current_text) > max_total_chars:
            # 删除最旧的文本，保留最新的
            self.log_text.setPlainText(current_text[-(max_total_chars // 2):])

        # 滚动到底部
        self.log_text.ensureCursorVisible()