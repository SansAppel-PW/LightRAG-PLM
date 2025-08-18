def do_parse(
        output_dir,
        pdf_file_names: list[str],
        pdf_bytes_list: list[bytes],
        p_lang_list: list[str],
        backend="pipeline",
        parse_method="auto",
        formula_enable=True,
        table_enable=True,
        server_url=None,
        f_draw_layout_bbox=True,
        f_draw_span_bbox=True,
        f_dump_md=True,
        f_dump_middle_json=True,
        f_dump_model_output=True,
        f_dump_orig_pdf=True,
        f_dump_content_list=True,
        f_make_md_mode=MakeMode.MM_MD,
        start_page_id=0,
        end_page_id=None,
        **kwargs,
):
    # 预处理PDF字节数据
    pdf_bytes_list = _prepare_pdf_bytes(pdf_bytes_list, start_page_id, end_page_id)

    if backend == "naive":
        _process_naive(

        )
    # elif backend == "pipeline":
    #     _process_pipeline(
    #         output_dir, pdf_file_names, pdf_bytes_list, p_lang_list,
    #         parse_method, formula_enable, table_enable,
    #         f_draw_layout_bbox, f_draw_span_bbox, f_dump_md, f_dump_middle_json,
    #         f_dump_model_output, f_dump_orig_pdf, f_dump_content_list, f_make_md_mode
    #     )
    # else:
    #     if backend.startswith("vlm-"):
    #         backend = backend[4:]
    #
    #     os.environ['MINERU_VLM_FORMULA_ENABLE'] = str(formula_enable)
    #     os.environ['MINERU_VLM_TABLE_ENABLE'] = str(table_enable)
    #
    #     _process_vlm(
    #         output_dir, pdf_file_names, pdf_bytes_list, backend,
    #         f_draw_layout_bbox, f_draw_span_bbox, f_dump_md, f_dump_middle_json,
    #         f_dump_model_output, f_dump_orig_pdf, f_dump_content_list, f_make_md_mode,
    #         server_url, **kwargs,
    #     )


def _process_naive(
        output_dir,
        pdf_file_names,
        pdf_bytes_list,
        p_lang_list,
        parse_method,
        p_formula_enable,
        p_table_enable,
        f_draw_layout_bbox,
        f_draw_span_bbox,
        f_dump_md,
        f_dump_middle_json,
        f_dump_model_output,
        f_dump_orig_pdf,
        f_dump_content_list,
        f_make_md_mode,
):
    """处理 naive 后端逻辑"""
    from plm.utils.session.postgre_db import PostgreDataBase
    from plm.conf.settings import rep_settings
    from plm.models import Base
    db = PostgreDataBase(rep_settings.POSTGRE_DATABASE_URL)
    Base.metadata.create_all(db.engine)

    """ 获取所有docx文件路径 """
