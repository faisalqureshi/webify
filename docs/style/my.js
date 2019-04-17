$(document).ready(function(){

    $("#toggle-news").css('cursor', 'pointer');
    $("#toggle-about").css('cursor', 'pointer');

    // toggle news
    $("#toggle-news").click( function() {
        
        if ( $("#toggle-news").text() == "more >>>" ) {
            $(".old-news").each( function(){
                $(this).show()
            });
            $("#toggle-news").text("<<< less");
        }
        else {
            $(".old-news").each( function(){
                $(this).hide()
            });
            $("#toggle-news").text("more >>>");
        }
    });

    // toggle about
    $("#toggle-about").click(function(){

        if ( $("#toggle-about").text() == "more >>>" ) {
            $(".about-more").each( function() {
                $(this).show()
            });
            $("#toggle-about").text("<<< less");
        }
        else {
            $(".about-more").each( function() {
                $(this).hide()
            });
            $("#toggle-about").text("more >>>");
        }
    });
});


$(document).ready(function(){
  // Add smooth scrolling to all links
  $("a").on('click', function(event) {

    // Make sure this.hash has a value before overriding default behavior
    //console.log(window.location.pathname)
    //console.log(this.pathname)
    //console.log(this.hash)

    if (this.hash !== "" && this.pathname == window.location.pathname) {
      // Prevent default anchor click behavior
      event.preventDefault();

      // Store hash
      var hash = this.hash;

      // Using jQuery's animate() method to add smooth page scroll
      // The optional number (800) specifies the number of milliseconds it takes to scroll to the specified area
      $('html, body').animate({
        scrollTop: $(hash).offset().top
      }, 800, function(){
   
        // Add hash (#) to URL when done scrolling (default click behavior)
        window.location.hash = hash;
      });
    } // End if
  });
});
