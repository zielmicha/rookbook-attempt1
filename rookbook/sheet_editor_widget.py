from typing import *
from rookcore import record
from rookcore.reactive import reactive, VarRef, stabilise
from rookbook import core
from rookwidget.core import h, widget, Widget, mount_root_widget, WidgetDef, Ref, WidgetArgs

class CellDescription(NamedTuple):
    uuid: str
    code_ref: Ref[str]
    rendered_widget: WidgetDef

class SheetEditorWidget(Widget):
    def init(self, focus_var, cells: List[CellDescription]):
        self.focus_var = focus_var
        self.cells = cells

    def render(self):
        return h('div',
                 *[ widget(CellWidget,
                           key=cell.uuid,
                           rendered_widget=cell.rendered_widget,
                           code_ref=cell.code_ref)
                    for cell in self.cells ])

class CellWidget(Widget):
    def init(self, code_ref, rendered_widget):
        self.code_ref = code_ref
        self.rendered_widget = rendered_widget

    def render(self):
        return h('div',
                 h('textarea', self.code_ref.value,
                   {'onedit': self.event_handler('_edit'),
                    'onkeyup': self.event_handler('_key_up')}),
                 h('div', self.rendered_widget))

    def _edit(self, event):
        self.code_ref.value = event.target.value
        stabilise()

    def _key_up(self, event):
        # todo: handle up arrow specially
        self.code_ref.value = event.target.value
        stabilise()

def make_cell_description(cell_widget_types, cell_info: core.RemoteCellInfo) -> CellDescription:
    print(cell_info)
    _, widget_type = cell_widget_types[cell_info.cell_widget_type]

    rendered_widget = WidgetDef(
        type_=widget_type,
        key='widget',
        args=[cell_info.widget_data],
        kwargs={},
    )

    return CellDescription(
        uuid=cell_info.uuid,
        code_ref=reactive(lambda: cell_info.code),
        rendered_widget=rendered_widget,
    )

async def make_editor_widget(cell_widget_types, sheet):
    cell_infos = await sheet.get_cells()

    focus_var = VarRef(0)
    cells = reactive(
        lambda: [ make_cell_description(cell_widget_types, cell_info) for cell_info in cell_infos.value ])

    return SheetEditorWidget(reactive(lambda: WidgetArgs.make(focus_var, cells.value)))
