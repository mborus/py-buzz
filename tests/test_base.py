import pytest
import traceback

from buzz.base import Buzz


class TestBuzz:

    def test_formatting(self):
        with pytest.raises(Buzz) as err_info:
            raise Buzz('fail message with no formatting')
        assert 'fail message with no formatting' in str(err_info.value)

        with pytest.raises(Buzz) as err_info:
            raise Buzz('fail message with {}', 'arg formatting')
        assert 'fail message with arg formatting' in str(err_info.value)

        with pytest.raises(Buzz) as err_info:
            raise Buzz('fail message with {fmt}', fmt='kwarg formatting')
        assert 'fail message with kwarg formatting' in str(err_info.value)

    def test_require_condition(self):
        Buzz.require_condition(True, 'should not fail')
        with pytest.raises(Buzz) as err_info:
            Buzz.require_condition(False, 'fail message with {}', 'formatting')
        assert 'fail message with formatting' in str(err_info.value)

    def test_handle_errors__no_exceptions(self):
        with Buzz.handle_errors('no errors should happen here'):
            pass

    def test_handle_errors__basic_handling(self):
        with pytest.raises(Buzz) as err_info:
            with Buzz.handle_errors('intercepted exception'):
                raise ValueError("there was a problem")
        assert 'there was a problem' in str(err_info.value)
        assert 'intercepted exception' in str(err_info.value)
        assert 'ValueError' in str(err_info.value)

    def test_handle_errors__with_do_else(self):
        check_list = []
        with Buzz.handle_errors(
            'no errors should happen here, but do_else should be called',
            do_else=lambda: check_list.append(1)
        ):
            pass
        assert check_list == [1]

    def test_handle_errors__with_do_finally(self):
        check_list = []
        with Buzz.handle_errors(
            'no errors should happen here, but do_finally should be called',
            do_finally=lambda: check_list.append(1)
        ):
            pass
        assert check_list == [1]

        check_list = []
        with pytest.raises(Buzz) as err_info:
            with Buzz.handle_errors(
                'intercepted exception',
                do_finally=lambda: check_list.append(1)
            ):
                raise Exception("there was a problem")
        assert 'there was a problem' in str(err_info.value)
        assert 'intercepted exception' in str(err_info.value)
        assert check_list == [1]

    def test_handle_errors__with_do_except(self):
        check_list = []
        with Buzz.handle_errors(
            'no errors should happen here, so do_except should not be called',
            do_except=lambda e, m, t: check_list.append(m),
        ):
            pass
        assert check_list == []

        check_list = []
        with pytest.raises(Buzz) as err_info:
            with Buzz.handle_errors(
                'intercepted exception',
                do_except=lambda e, m, t: check_list.append(m),
            ):
                raise Exception("there was a problem")
        assert 'there was a problem' in str(err_info.value)
        assert 'intercepted exception' in str(err_info.value)
        assert len(check_list) == 1
        assert 'there was a problem' in check_list[0]

    def test_handle_errors__without_reraise(self):
        check_list = []
        with Buzz.handle_errors(
            'intercepted exception',
            re_raise=False,
            do_except=lambda e, m, t: check_list.append(m),
        ):
            raise Exception("there was a problem")
        assert len(check_list) == 1
        assert 'there was a problem' in check_list[0]

    def test_handle_errors__with_specific_exception_class(self):
        class SpecialError(Exception):
            pass

        with pytest.raises(Exception) as err_info:
            with Buzz.handle_errors(
                'there was a problem',
                exception_class=SpecialError,
            ):
                raise Exception("there was a problem")
        assert err_info.type == Exception

        with pytest.raises(Exception) as err_info:
            with Buzz.handle_errors(
                'there was a problem',
                exception_class=SpecialError,
            ):
                raise SpecialError("there was a problem")
        assert err_info.type == Buzz

    def test_handle_errors__error_formatting_message(self):
        with pytest.raises(Buzz) as err_info:
            with Buzz.handle_errors('{format_arg1}', format_arg2='foo'):
                raise ValueError("there was a problem")
        assert err_info.type == Buzz
        assert 'Failed while formatting message' in str(err_info.value)

    def test_accumulate_errors(self):
        with pytest.raises(Buzz) as err_info:
            with Buzz.accumulate_errors('there will be errors') as checker:
                checker += True
                checker += False
                checker += 1 == 2
                checker += 'cooooooool'
                checker += 0
        err_msg = err_info.value.message
        assert 'there will be errors' in err_msg
        assert '`checker += True` resolved as false' not in err_msg
        assert '`checker += False` resolved as false' in err_msg
        assert '`checker += 1 == 2` resolved as false' in err_msg
        assert '`checker += \'cooooooool\' resolved as false' not in err_msg
        assert '`checker += 0` resolved as false' in err_msg

    def test_check_expressions(self):
        with pytest.raises(Buzz) as err_info:
            with Buzz.check_expressions(
                    main_message='there will be errors',
            ) as check:
                check(True)
                check(False)
                check(1 == 2, "one is not two")
                check('cooooooool', 'not a problem')
                check(0, "zero is still zero")
        err_msg = err_info.value.message
        assert 'there will be errors' in err_msg
        assert '1st expression failed' not in err_msg
        assert '2nd expression failed' in err_msg
        assert 'one is not two' in err_msg
        assert 'not a problem' not in err_msg
        assert 'zero is still zero' in err_msg

    def test_nested_handler(self):
        """
        This test verifies that a handler that is nested inside another buzz
        catching mechanism properly sanitizes the final error string so that
        format arguments in the outside mechanism don't get caught up in
        curly braces in the final error string
        """
        with pytest.raises(Buzz) as err_info:
            with Buzz.handle_errors("outside handler"):
                with Buzz.handle_errors("inside handler"):
                    raise Exception("this has {curlies}")
        assert 'this has {curlies}' in err_info.value.message

    def test_reformat_exception(self):
        final_message = Buzz.reformat_exception(
            "I want this to be included (with {format_arg})",
            Exception("Original Error"),
            format_arg='blah',
        )
        assert 'I want this to be included (with blah)' in final_message
        assert 'Original Error' in final_message

    def test_get_traceback(self):
        try:
            raise Buzz("Original Error")
        except Exception as err:
            trace = err.get_traceback()
        last_frame = traceback.format_tb(trace)[-1]
        assert 'test_base.py' in last_frame
        assert 'test_get_traceback' in last_frame
        assert 'Buzz("Original Error")' in last_frame
