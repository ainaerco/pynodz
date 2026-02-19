def test_node_mime_data_set_get_object(qtbot):
    from nodeUtils import NodeMimeData

    mime = NodeMimeData()
    obj = {"key": "value"}
    mime.setObject(obj)
    assert mime.getObject() == obj


def test_node_mime_data_set_origin(qtbot):
    from qtpy.QtCore import QPointF
    from nodeUtils import NodeMimeData

    mime = NodeMimeData()
    mime.setOrigin(QPointF(10, 20))
    assert mime.origin.x() == 10 and mime.origin.y() == 20
