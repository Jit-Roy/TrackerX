from PySide6.QtCore import Qt, QPoint, QRect, QSize, QMargins
from PySide6.QtWidgets import QLayout, QSizePolicy, QLayoutItem


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        spacing = self.spacing()

        if not self._item_list:
            return 0

        # Calculate the block width for centering the entire grid
        sample_item_w = self._item_list[0].sizeHint().width()
        available_w = rect.width()
        
        cols = max(1, (available_w + spacing) // (sample_item_w + spacing))
        block_w = cols * sample_item_w + (cols - 1) * spacing
        
        # The starting X offset to center the entire block
        start_x = rect.x() + max(0, (available_w - block_w) // 2)

        current_x = start_x
        current_y = rect.y()
        line_height = 0

        for item in self._item_list:
            wid = item.widget()
            space_x = spacing
            if wid:
                space_x = spacing if spacing != -1 else wid.style().layoutSpacing(
                    QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            
            item_w = item.sizeHint().width()
            
            if current_x + item_w > start_x + block_w and current_x > start_x:
                # Wrap to next line
                current_x = start_x
                current_y += line_height + spacing
                line_height = 0
                
            if not test_only:
                item.setGeometry(QRect(QPoint(current_x, current_y), item.sizeHint()))
                
            current_x += item_w + space_x
            line_height = max(line_height, item.sizeHint().height())

        return current_y + line_height - rect.y()
