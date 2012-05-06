/**
* DAB game
*/

var global_timeout = 5000;
var retry_limit = 4; /* global retry number */

function random_int (min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function keys(obj) {
    var ret = [];
    for(var k in obj) {
        if (obj.hasOwnProperty(k)) {
            ret.push(k);
        }
    }
    return ret;
}

function do_query(url, complete_callback, kwargs) {
    var all_kwargs = {
        url: url,
        type: 'get',
        dataType: 'jsonp',
        timeout: global_timeout,
        success: function(data) {
            console.log('successful ajax query to ' + url);
            complete_callback(null, data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log('failed query to ' + url);
            complete_callback(errorThrown, null);
            redo(retry_limit);
        },
        complete: function(jqXHR, textStatus) {
            // TODO: error handling (jsonp doesn't get error() calls for a lot of errors)
        },
        headers: { 'User-Agent': 'DAB/0.0.0 stephen laporte stephen.laporte@gmail.com' }
    };

    for (var key in kwargs) {
        if(kwargs.hasOwnProperty(key)) {
            all_kwargs[key] = kwargs[key];
        }
    }
    $.ajax(all_kwargs);
}

/*
 get list of pages needing fix
 	 http://en.wikipedia.org/wiki/Category:Articles_with_links_needing_disambiguation_from_June_2011
 get random page to fix
 get the dab link
 	$('span:contains("disambiguation needed")').parents('sup').prev('a')
 get the dab page
 */

function dab(article) {
	var title_fm = article.title;
	var title =	article.title.replace(/ /g, '_');
	var page = article.pageid;
	var choices, 
		found_phrase,
		page_content,
		dab_page_title;

	function process_dab_page(err, data) {
		console.log('processing the dab page')
		var page_id = keys(data['query']['pages']);
		var dab_content = data['query']['pages'][page_id]['revisions']['0']['*'];

		choices = dab_content.match(/\*.*\n/gi);
		
		render();
	}

	function process_page(err, data) {
		console.log('processing the page')
		var page_id = keys(data['query']['pages']);
		var page_content = data['query']['pages'][page_id]['revisions']['0']['*'];
		if(page_content.match(/<ol><li>REDIRECT/gi)) {
			//look at headnote too
			console.log('no redirects, please');
			redo(retry_limit);
		} else {
			dab_page_title = $('span:contains("disambiguation needed")', page_content).parents('sup').prev('a').attr('title').replace(' ', '_');
			do_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=' + dab_page_title + '&rvprop=content&format=json', process_dab_page)
			found_phrase = $('a[href="/wiki/' + dab_page_title + '"]', page_content).parent();
			if(!found_phrase) {
				redo(retry_limit);
			} else {
				console.log('found ' + title_fm + ' in ' + dab_page_title);
			}
		}
	}

	function render(err) {
		$('#phrase').html('<p><em>In the phrase</em></p><p id="phrase-content"></p>');
		$('#phrase-content').html(found_phrase);
		$('#phrase-content a[href="/wiki/' + dab_page_title + '"]').css('background-color', 'yellow');
		$('#inst').html('<p><em>Does the highlighted link mean:</em></p>');
		for(var i = 0; i < choices.length; i++) {
			$('#as').append('<li>' + choices[i] + '</li>');
		}
		console.log('preparing html');
	}

	do_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvparse&pageids=' + page + '&rvprop=content&format=json', process_page);
}

function get_dabs() {
	do_query('http://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:Articles_with_links_needing_disambiguation_from_June_2011&prop=info&cmlimit=500&format=json', process_dabs);
}

function process_dabs(err, data) {
	var articles = data['query']['categorymembers'];
	// save article list?
	console.log('choosing among ' + articles.length + ' articles with links to fix');	
	var quiz = new dab(articles[random_int(0, articles.length - 1)]);
}

function redo(limit) {
	console.log('redoing');
	if(limit > 0 ) {
		retry_limit -= 1;
		console.log('Something is awry! ' + retry_limit +' retries left');
		get_dabs();
	} else {
		$('#phrase').html('<h1>I just give up....</h1>');
	}
	
}

function edit () {
	$.ajax({
	  url: 'http://en.wikipedia.org/w/api.php',
	  data: 'action=query&prop=info|revisions&rvprop=content&intoken=edit&titles=User:Slaporte&format=jsonp',
	  success: function( data ) {
	      myToken = data;
	  }
	});

	var sendData = {
	  action: 'edit',
	  format: 'json',
	  title: myPageName,
	  text: myPageText,
	  summary: myEditSummary,
	  token: '+\\'
	};

	$.ajax({
	  url: 'http://en.wikipedia.org/w/api.php',
	  data: sendData,
	  dataType: 'json',
	  type: 'POST',
	  success: function( data ) {
	    if ( data.edit.result == "Success" ) {
	      // Do something else
	    } else {
	      console.debug( 'Unknown result from API.' );
	    }
	  },
	  error: function( xhr ) {
	    console.debug( 'Edit failed.' );
	    console.debug( xhr.responseText );
	  }
	});
}

get_dabs();