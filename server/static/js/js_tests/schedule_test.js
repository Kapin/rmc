define(function(require) {
  var expect = require('ext/chai').expect;
  var $ = require('ext/jquery');
  var schedule_parser = require('schedule_parser');

  describe('Schedule parsing', function() {
    var parsedSchedulePromise = $.get(
        '/static/sample_schedule.txt').then(function(r) {
      return schedule_parser.parseSchedule(r);
    });

    var testParsedScheduleAsync = function(testName, testCallback) {
      it(testName, function(done) {
        parsedSchedulePromise.then(function(scheduleData) {
          try {
            testCallback(scheduleData);
            done();
          } catch (e) {
            return done(e);
          }
        });
      });
    };

    testParsedScheduleAsync('extracts the term name',
        function(scheduleData) {
      expect(scheduleData.term_name).to.equal("Winter 2014");
    });

    testParsedScheduleAsync('produces no failed items',
        function(scheduleData) {
      expect(scheduleData.failed_items.length).to.equal(0);
    });

    testParsedScheduleAsync('extracts the correct number of items',
        function(scheduleData) {
      expect(scheduleData.processed_items.length).to.equal(343);
    });

    testParsedScheduleAsync('extracts the first item\'s building',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].building).to.equal("OPT");
    });

    testParsedScheduleAsync('extracts the first item\'s course ID',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].course_id).to.equal("cs138");
    });

    testParsedScheduleAsync('extracts the first item\'s prof name',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].prof_name).to.equal(
        "Michael Godfrey");
    });

    testParsedScheduleAsync('extracts the first item\'s start date',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].start_date).to.equal(1389106800);
    });

    testParsedScheduleAsync('extracts the first item\'s end date',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].end_date).to.equal(1389111600);
    });

    testParsedScheduleAsync('extracts the first item\'s class number',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].class_num).to.equal('5819');
    });

    testParsedScheduleAsync('extracts the first item\'s room',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].room).to.equal('347');
    });

    testParsedScheduleAsync('extracts the first item\'s section number',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].section_num).to.equal('001');
    });

    testParsedScheduleAsync('extracts the first item\'s section type',
        function(scheduleData) {
      expect(scheduleData.processed_items[0].section_type).to.equal('LEC');
    });

    testParsedScheduleAsync('extracts the last item\'s building',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].building).to.equal("DC");
    });

    testParsedScheduleAsync('extracts the last item\'s course ID',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].course_id).to.equal("stat230");
    });

    testParsedScheduleAsync('extracts the last item\'s prof name',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].prof_name).to.equal(
          "Christian Boudreau");
    });

    testParsedScheduleAsync('extracts the last item\'s start date',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].start_date).to.equal(
          1396629000);
    });

    testParsedScheduleAsync('extracts the last item\'s end date',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].end_date).to.equal(1396632000);
    });

    testParsedScheduleAsync('extracts the last item\'s class number',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].class_num).to.equal('7208');
    });

    testParsedScheduleAsync('extracts the last item\'s room',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].room).to.equal('1350');
    });

    testParsedScheduleAsync('extracts the last item\'s section number',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].section_num).to.equal('002');
    });

    testParsedScheduleAsync('extracts the last item\'s section type',
        function(scheduleData) {
      expect(scheduleData.processed_items[342].section_type).to.equal('LEC');
    });
  });
});
