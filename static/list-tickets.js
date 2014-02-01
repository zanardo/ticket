window.onscroll = function(){
	e = document.getElementById("topfixedblock");
	if(window.pageYOffset > 0)
		e.style.boxShadow = "0px 0px 5px #A6A6A6";
	else
		e.style.boxShadow = '';
}